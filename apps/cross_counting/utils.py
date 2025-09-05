"""
Time-series utilities for CrossCountingData analytics
Delta-based occupancy with midnight reset + negative-floor correction (no schema change required)
"""

import logging
from collections import defaultdict
from datetime import timedelta, datetime, date
from typing import List, Dict, Any

from django.db import connection
from django.utils import timezone
from django.utils.timezone import localtime

logger = logging.getLogger(__name__)

# ----------------------------------------------------
# Configuration (tune per deployment if needed)
# ----------------------------------------------------
NEGATIVE_FLOOR_T = 20          # net should never go below -T after correction
GRACE_MINUTES_AFTER_MIDNIGHT = 20  # skip correction in first N minutes after midnight
MAX_CORRECTION_PER_CALL = 300  # safety cap to avoid runaway corrections in a single call


# ------------------------------
# Generic serializers
# ------------------------------
def serialize_datetime_data(data):
    """Recursively serialize datetime/UUID for JSON responses."""
    import uuid
    if isinstance(data, datetime):
        return data.isoformat()
    elif isinstance(data, date):
        return data.isoformat()
    elif isinstance(data, uuid.UUID):
        return str(data)
    elif isinstance(data, dict):
        return {k: serialize_datetime_data(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [serialize_datetime_data(x) for x in data]
    return data


# ------------------------------
# Analytics helpers
# ------------------------------
class CrossCountingAnalytics:
    @staticmethod
    def refresh_materialized_views():
        """Refresh materialized views for dashboard queries."""
        with connection.cursor() as cursor:
            cursor.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY cross_counting_hourly_aggregates;")
            cursor.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY cross_counting_daily_peaks;")

    @staticmethod
    def get_camera_activity_summary(camera_ids: List[str], hours: int = 24) -> List[Dict[str, Any]]:
        """Activity summary for multiple cameras over specified hours (raw cumulative stats)."""
        since = timezone.now() - timedelta(hours=hours)
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT c.name as camera_name,
                       c.id as camera_id,
                       COUNT(ccd.id) as data_points,
                       MAX(ccd.cc_total_count) as peak_total,
                       MAX(ccd.cc_in_count) as peak_in,
                       MAX(ccd.cc_out_count) as peak_out,
                       MIN(ccd.created_at) as first_data,
                       MAX(ccd.created_at) as last_data,
                       AVG(ccd.cc_total_count) as avg_total
                FROM cross_counting_data_timeseries ccd
                JOIN cross_counting_camera c ON ccd.camera_id = c.id
                WHERE ccd.created_at >= %s
                  AND c.id = ANY (%s)
                GROUP BY c.id, c.name
                ORDER BY c.name
            """, [since, camera_ids])
            cols = [c[0] for c in cursor.description] if cursor.description else []
            return [dict(zip(cols, row)) for row in cursor.fetchall()]

    @staticmethod
    def get_system_health_metrics(minutes: int = 60) -> Dict[str, Any]:
        """System health metrics for ingestion."""
        since = timezone.now() - timedelta(minutes=minutes)
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*) as total_records,
                       COUNT(DISTINCT camera_id) as active_cameras,
                       COUNT(DISTINCT device_name) as active_devices,
                       MIN(created_at) as earliest_data,
                       MAX(created_at) as latest_data,
                       AVG(EXTRACT(EPOCH FROM (created_at - alarm_time))) as avg_processing_delay_seconds,
                       COUNT(CASE WHEN alarm_status = true THEN 1 END) as active_alarms
                FROM cross_counting_data_timeseries
                WHERE created_at >= %s
            """, [since])
            row = cursor.fetchone()
            cols = [c[0] for c in cursor.description] if cursor.description else []
            return dict(zip(cols, row)) if row else {}

    @staticmethod
    def optimize_table_maintenance():
        """Basic ANALYZE + size stats."""
        with connection.cursor() as cursor:
            cursor.execute("ANALYZE cross_counting_data_timeseries;")
            cursor.execute("""
                SELECT 
                    pg_size_pretty(pg_total_relation_size('cross_counting_data_timeseries')) as total_size,
                    pg_size_pretty(pg_relation_size('cross_counting_data_timeseries')) as table_size,
                    pg_size_pretty(pg_indexes_size('cross_counting_data_timeseries')) as indexes_size
            """)
            cols = [c[0] for c in cursor.description] if cursor.description else []
            row = cursor.fetchone()
            return dict(zip(cols, row)) if row else {}


# ------------------------------
# Delta-first utilities
# ------------------------------
class TablePartitioningManager:
    """
    Delta-based occupancy & aggregates without schema changes.
    Assumptions:
      - Devices reset cumulative counters to 0 at local midnight.
      - We compute deltas from FIRST-of-day cumulative to LATEST-of-now cumulative per camera.
      - Region-level negative-floor correction bounds net to >= -T for display, without mutating DB.
    """

    # ---------- PUBLIC APIs used by your views ----------

    @staticmethod
    def get_current_occupancy_data() -> List[Dict[str, Any]]:
        """
        Current occupancy per region for public display (delta since local midnight).

        Steps:
          - Window = [today local midnight .. now]
          - Per active camera: FIRST cumulative of day & LATEST cumulative of now
          - ΔIN = max(0, latest_in - first_in), ΔOUT = max(0, latest_out - first_out)
          - Region SUMs: ΣΔIN, ΣΔOUT
          - NEGATIVE-FLOOR: ensure net >= -NEGATIVE_FLOOR_T via just-enough virtual IN (display only)
          - Region occupancy = max(0, corrected_net)
          - Display cap by region.occupancy
        """
        from .models import Region, Camera

        results = []

        now = timezone.now()
        local_now = localtime(now)
        local_midnight = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
        start = timezone.make_aware(local_midnight.replace(tzinfo=None)) if local_midnight.tzinfo is None else local_midnight
        end = now

        minutes_since_midnight = int((local_now - local_midnight).total_seconds() // 60)
        apply_correction = minutes_since_midnight >= GRACE_MINUTES_AFTER_MIDNIGHT

        regions = Region.objects.all()
        for region in regions:
            cameras = list(Camera.objects.filter(region=region, status=True).values_list('id', flat=True))
            if not cameras:
                results.append({
                    "region_name": region.name,
                    "current_count": 0,
                    "max_occupancy": region.occupancy,
                    "occupancy_percentage": 0.0,
                    "total_in_count": 0,
                    "total_out_count": 0,
                    "occupancy_by_in_out": 0,
                    "calculation_method": "delta_since_midnight",
                    "available_count": region.occupancy,
                    "correction_applied": False,
                    "correction_value": 0,
                })
                continue

            per_cam = TablePartitioningManager._first_and_latest_for_cameras(cameras, start, end)

            sum_in_delta = 0
            sum_out_delta = 0
            for row in per_cam:
                first_in = row['first_in'] or 0
                first_out = row['first_out'] or 0
                last_in = row['last_in'] if row['last_in'] is not None else first_in
                last_out = row['last_out'] if row['last_out'] is not None else first_out

                din = max(0, (last_in - first_in))
                dout = max(0, (last_out - first_out))
                sum_in_delta += din
                sum_out_delta += dout

            # --- Negative-floor correction (display only) ---
            net_raw = int(sum_in_delta - sum_out_delta)
            correction = 0
            if apply_correction and net_raw < -NEGATIVE_FLOOR_T:
                # Just-enough correction so that net >= -T, capped for safety
                correction = min(max(0, -(net_raw + NEGATIVE_FLOOR_T)), MAX_CORRECTION_PER_CALL)

            corrected_in = int(sum_in_delta + correction)
            net_corrected = int(corrected_in - sum_out_delta)

            # Final occupancy shown
            occ_display = max(0, net_corrected)
            current_count = min(occ_display, region.occupancy)

            occ_pct = (current_count / region.occupancy * 100) if region.occupancy > 0 else 0.0
            occ_pct = min(occ_pct, 100.0)
            available = max(0, region.occupancy - int(current_count))

            results.append({
                "region_name": region.name,
                "current_count": int(current_count),
                "max_occupancy": region.occupancy,
                "occupancy_percentage": round(occ_pct, 1),
                # Expose both original deltas and corrected IN for transparency in UI if needed
                "total_in_count": int(corrected_in),      # corrected (display)
                "total_out_count": int(sum_out_delta),    # raw delta
                "occupancy_by_in_out": int(occ_display),  # corrected occupancy
                "calculation_method": "delta_since_midnight + negative_floor",
                "available_count": available,
                "correction_applied": bool(correction),
                "correction_value": int(correction),
                "original_in_delta": int(sum_in_delta),   # optional: for debugging / admin UI
                "original_net": int(net_raw),
                "net_after_correction": int(net_corrected),
            })

        return results

    @staticmethod
    def get_enhanced_dashboard_data() -> List[Dict[str, Any]]:
        """
        Enhanced dashboard data with occupancy analysis and camera details.
        Returns datetime objects for template filters like |timesince.
        """
        from .models import Region, Camera, CrossCountingData

        regions = Region.objects.all()
        occ_list = TablePartitioningManager.get_current_occupancy_data()
        occ_map = {row['region_name']: row for row in occ_list}
        enhanced = []

        for region in regions:
            cameras_qs = Camera.objects.filter(region=region, status=True)
            camera_details = []
            for cam in cameras_qs:
                latest = CrossCountingData.objects.filter(camera=cam).order_by('-created_at').first()
                camera_details.append({
                    'id': str(cam.id),
                    'name': cam.name,
                    'status': 'active' if cam.status else 'inactive',
                    'latest_in_count': latest.cc_in_count if latest else 0,
                    'latest_out_count': latest.cc_out_count if latest else 0,
                    'latest_total_count': latest.cc_total_count if latest else 0,
                    'last_updated': latest.created_at if latest else None
                })

            occ = occ_map.get(region.name)
            if occ:
                enhanced.append({
                    'region_id': region.id,
                    'region_name': region.name,
                    'max_occupancy': region.occupancy,
                    'current_occupancy': occ['current_count'],
                    'occupancy_percentage': occ['occupancy_percentage'],
                    'total_in_count': occ['total_in_count'],
                    'total_out_count': occ['total_out_count'],
                    'occupancy_by_in_out': occ['occupancy_by_in_out'],
                    'camera_count': cameras_qs.count(),
                    'status': 'active' if occ['current_count'] > 0 else 'empty',
                    'calculation_method': occ.get('calculation_method', 'delta_since_midnight + negative_floor'),
                    'cameras': camera_details
                })
            else:
                enhanced.append({
                    'region_id': region.id,
                    'region_name': region.name,
                    'max_occupancy': region.occupancy,
                    'current_occupancy': 0,
                    'occupancy_percentage': 0.0,
                    'total_in_count': 0,
                    'total_out_count': 0,
                    'occupancy_by_in_out': 0,
                    'camera_count': cameras_qs.count(),
                    'status': 'empty',
                    'calculation_method': 'delta_since_midnight + negative_floor',
                    'cameras': camera_details
                })

        # Keep datetimes for template |timesince
        return enhanced

    @staticmethod
    def get_enhanced_dashboard_data_serialized() -> List[Dict[str, Any]]:
        """
        Enhanced dashboard data with datetime serialization for JSON APIs.
        """
        enhanced = TablePartitioningManager.get_enhanced_dashboard_data()
        return serialize_datetime_data(enhanced)

    @staticmethod
    def get_dashboard_statistics() -> Dict[str, Any]:
        """High-level stats + current occupancy (serialized for templates that expect plain data)."""
        from .models import Region, Camera, CrossCountingData

        total_regions = Region.objects.count()
        total_cameras = Camera.objects.count()
        active_cameras = Camera.objects.filter(status=True).count()

        since_24h = timezone.now() - timedelta(hours=24)
        recent_points = CrossCountingData.objects.filter(created_at__gte=since_24h).count()

        health = CrossCountingAnalytics.get_system_health_metrics(minutes=60)
        volume = DataRetentionManager.get_data_volume_stats()
        occ = TablePartitioningManager.get_current_occupancy_data()
        total_current_occupancy = sum(item['current_count'] for item in occ)

        result = {
            'total_regions': total_regions,
            'total_cameras': total_cameras,
            'active_cameras': active_cameras,
            'recent_data_points': recent_points,
            'health_metrics': health,
            'volume_stats': volume,
            'occupancy_data': occ,
            'total_current_occupancy': total_current_occupancy
        }
        return serialize_datetime_data(result)

    # ---------- Hourly / Daily analytics (delta-based) ----------

    @staticmethod
    def get_hourly_region_aggregates(region_id: int, start_time, end_time) -> Dict[str, Any]:
        """
        Hourly aggregated IN/OUT **deltas** for all cameras in a region.
        Uses LAG over per-camera hourly last cumulative to compute per-hour movement.
        """
        from .models import Camera

        if start_time.tzinfo is None:
            start_time = timezone.make_aware(start_time)
        if end_time.tzinfo is None:
            end_time = timezone.make_aware(end_time)

        cam_ids = list(Camera.objects.filter(region_id=region_id, status=True).values_list('id', flat=True))
        if not cam_ids:
            return serialize_datetime_data({
                "hourly_data": [{"hour": h, "total_in_delta": 0, "total_out_delta": 0} for h in range(24)],
                "region_name": "",
                "camera_count": 0,
                "individual_camera_data": []
            })

        with connection.cursor() as cursor:
            cursor.execute("""
                WITH hourly_last AS (
                  SELECT camera_id,
                         DATE_TRUNC('hour', created_at) AS hour_ts,
                         MAX(created_at) AS last_ts
                  FROM cross_counting_data_timeseries
                  WHERE camera_id = ANY(%s)
                    AND created_at >= %s
                    AND created_at < %s
                  GROUP BY camera_id, DATE_TRUNC('hour', created_at)
                ),
                hourly_cum AS (
                  SELECT ccd.camera_id,
                         hl.hour_ts,
                         ccd.cc_in_count  AS in_cum,
                         ccd.cc_out_count AS out_cum
                  FROM hourly_last hl
                  JOIN cross_counting_data_timeseries ccd
                    ON ccd.camera_id = hl.camera_id AND ccd.created_at = hl.last_ts
                ),
                hourly_delta AS (
                  SELECT camera_id,
                         hour_ts,
                         GREATEST(in_cum  - LAG(in_cum)  OVER (PARTITION BY camera_id ORDER BY hour_ts),  0) AS in_delta,
                         GREATEST(out_cum - LAG(out_cum) OVER (PARTITION BY camera_id ORDER BY hour_ts), 0) AS out_delta
                  FROM hourly_cum
                ),
                region_hourly AS (
                  SELECT EXTRACT(HOUR FROM hour_ts)::int AS hour,
                         SUM(in_delta)::bigint  AS total_in_delta,
                         SUM(out_delta)::bigint AS total_out_delta
                  FROM hourly_delta
                  GROUP BY EXTRACT(HOUR FROM hour_ts)
                ),
                all_hours AS (SELECT generate_series(0, 23) AS hour)
                SELECT ah.hour,
                       COALESCE(rh.total_in_delta, 0)  AS total_in_delta,
                       COALESCE(rh.total_out_delta, 0) AS total_out_delta
                FROM all_hours ah
                LEFT JOIN region_hourly rh ON rh.hour = ah.hour
                ORDER BY ah.hour;
            """, [cam_ids, start_time, end_time])

            hourly = []
            for row in cursor.fetchall():
                hourly.append({
                    'hour': int(row[0]),
                    'total_in_delta': int(row[1]),
                    'total_out_delta': int(row[2]),
                })

        # Individual camera hourly deltas (for detail views)
        individual = []
        with connection.cursor() as cursor:
            cursor.execute("""
                WITH hourly_last AS (
                  SELECT camera_id,
                         DATE_TRUNC('hour', created_at) AS hour_ts,
                         MAX(created_at) AS last_ts
                  FROM cross_counting_data_timeseries
                  WHERE camera_id = ANY(%s)
                    AND created_at >= %s
                    AND created_at < %s
                  GROUP BY camera_id, DATE_TRUNC('hour', created_at)
                ),
                hourly_cum AS (
                  SELECT ccd.camera_id,
                         hl.hour_ts,
                         ccd.cc_in_count  AS in_cum,
                         ccd.cc_out_count AS out_cum
                  FROM hourly_last hl
                  JOIN cross_counting_data_timeseries ccd
                    ON ccd.camera_id = hl.camera_id AND ccd.created_at = hl.last_ts
                ),
                hourly_delta AS (
                  SELECT camera_id,
                         hour_ts,
                         GREATEST(in_cum  - LAG(in_cum)  OVER (PARTITION BY camera_id ORDER BY hour_ts),  0) AS in_delta,
                         GREATEST(out_cum - LAG(out_cum) OVER (PARTITION BY camera_id ORDER BY hour_ts), 0) AS out_delta
                  FROM hourly_cum
                )
                SELECT camera_id,
                       EXTRACT(HOUR FROM hour_ts)::int AS hour,
                       in_delta::bigint,
                       out_delta::bigint
                FROM hourly_delta
                ORDER BY camera_id, hour;
            """, [cam_ids, start_time, end_time])

            cam_map: Dict[str, List[Dict[str, int]]] = defaultdict(list)
            for cam_id, hour, d_in, d_out in cursor.fetchall():
                cam_map[str(cam_id)].append({
                    'hour': int(hour),
                    'in_delta': int(d_in),
                    'out_delta': int(d_out),
                })

        from .models import Camera
        cam_names = {str(cid): name for cid, name in Camera.objects.filter(id__in=cam_ids).values_list('id', 'name')}

        for cid, rows in cam_map.items():
            individual.append({
                'camera_id': cid,
                'camera_name': cam_names.get(cid, cid),
                'hourly_data': rows
            })

        # Region name (via any camera)
        region_name = ""
        first_cam = Camera.objects.filter(id__in=cam_ids).select_related('region').first()
        if first_cam and first_cam.region:
            region_name = first_cam.region.name

        return serialize_datetime_data({
            "hourly_data": hourly,
            "region_name": region_name,
            "camera_count": len(cam_ids),
            "individual_camera_data": individual
        })

    @staticmethod
    def get_daily_analysis_data(region_id: int, d: date) -> Dict[str, Any]:
        """
        Daily analysis:
          - per-camera peaks (cumulative)
          - delta-based regional hourly movement
        """
        from .models import Camera, CrossCountingData
        from django.db.models import Max

        cameras = Camera.objects.filter(region_id=region_id, status=True)
        if not cameras.exists():
            return serialize_datetime_data({
                "cameras": [],
                "summary": {},
                "simplified_analysis": {"individual_camera_data": [], "regional_hourly_data": []},
                "analysis_date": d,
                "analysis_type": "delta_hourly_with_peak_summary"
            })

        # Per-camera peak cumulative (for reporting)
        daily_data = []
        tot_peak_in = tot_peak_out = tot_peak_total = 0
        for cam in cameras:
            stats = CrossCountingData.objects.filter(
                camera=cam,
                created_at__date=d
            ).aggregate(
                peak_in_count=Max('cc_in_count'),
                peak_out_count=Max('cc_out_count'),
                peak_total_count=Max('cc_total_count')
            )
            if stats['peak_in_count'] is not None:
                daily_data.append({
                    "camera_name": cam.name,
                    "peak_in": stats['peak_in_count'],
                    "peak_out": stats['peak_out_count'],
                    "peak_total": stats['peak_total_count']
                })
                tot_peak_in += stats['peak_in_count'] or 0
                tot_peak_out += stats['peak_out_count'] or 0
                tot_peak_total += stats['peak_total_count'] or 0

        # Hourly delta-based movement for the day
        start_dt = timezone.make_aware(datetime.combine(d, datetime.min.time()))
        end_dt = start_dt + timedelta(days=1)
        hourly = TablePartitioningManager.get_hourly_region_aggregates(region_id, start_dt, end_dt)

        result = {
            "cameras": daily_data,
            "summary": {
                "total_peak_in": tot_peak_in,
                "total_peak_out": tot_peak_out,
                "total_peak_total": tot_peak_total,
                "active_cameras": len(daily_data)
            },
            "simplified_analysis": {
                "individual_camera_data": hourly.get("individual_camera_data", []),
                "regional_hourly_data": hourly.get("hourly_data", [])
            },
            "analysis_date": d,
            "analysis_type": "delta_hourly_with_peak_summary"
        }
        return serialize_datetime_data(result)

    @staticmethod
    def get_comparative_analysis_data(region_id: int, base_date: date, compare_date: date) -> Dict[str, Any]:
        """Compare two dates (peak summary + hourly deltas)."""
        base = TablePartitioningManager.get_daily_analysis_data(region_id, base_date)
        comp = TablePartitioningManager.get_daily_analysis_data(region_id, compare_date)

        comparison = []
        for base_cam in base["cameras"]:
            match = next(
                (c for c in comp["cameras"] if c["camera_name"] == base_cam["camera_name"]),
                {"peak_in": 0, "peak_out": 0, "peak_total": 0}
            )
            comparison.append({
                "camera_name": base_cam["camera_name"],
                "base_in": base_cam["peak_in"],
                "base_out": base_cam["peak_out"],
                "base_total": base_cam["peak_total"],
                "compare_in": match["peak_in"],
                "compare_out": match["peak_out"],
                "compare_total": match["peak_total"],
                "diff_in": match["peak_in"] - base_cam["peak_in"],
                "diff_out": match["peak_out"] - base_cam["peak_out"],
                "diff_total": match["peak_total"] - base_cam["peak_total"]
            })

        result = {
            "base_date": base_date,
            "compare_date": compare_date,
            "comparison": comparison,
            "base_summary": base["summary"],
            "compare_summary": comp["summary"],
            "base_hourly_aggregates": base.get("simplified_analysis", {}).get("regional_hourly_data", []),
            "compare_hourly_aggregates": comp.get("simplified_analysis", {}).get("regional_hourly_data", [])
        }
        return serialize_datetime_data(result)

    @staticmethod
    def get_comprehensive_analysis_data(region_id: int, from_date: date, to_date: date) -> Dict[str, Any]:
        """Multi-day wrap that reuses daily (delta hourly + peaks)."""
        from .models import Camera, CrossCountingData
        from django.db.models import Max
        from django.db.models.functions import TruncDate

        cameras = Camera.objects.filter(region_id=region_id, status=True)
        daily_trends = []

        for cam in cameras:
            daily = CrossCountingData.objects.filter(
                camera=cam,
                created_at__date__gte=from_date,
                created_at__date__lte=to_date
            ).annotate(
                date=TruncDate('created_at')
            ).values('date').annotate(
                peak_in_count=Max('cc_in_count'),
                peak_out_count=Max('cc_out_count'),
                peak_total_count=Max('cc_total_count')
            ).order_by('date')
            daily_trends.append({
                "camera_name": cam.name,
                "daily_data": list(daily)
            })

        total_days = (to_date - from_date).days + 1
        region_day_one = TablePartitioningManager.get_daily_analysis_data(region_id, from_date)

        result = {
            "from_date": from_date,
            "to_date": to_date,
            "total_days": total_days,
            "daily_trends": daily_trends,
            "cameras": [{"id": str(cam.id), "name": cam.name} for cam in cameras],
            "region_hourly_aggregates": region_day_one.get("simplified_analysis", {})
        }
        return serialize_datetime_data(result)

    # ---------- Internal helpers ----------

    @staticmethod
    def _first_and_latest_for_cameras(camera_ids: List[str], start_dt, end_dt) -> List[Dict[str, Any]]:
        """
        Get FIRST and LATEST cumulative counts between start_dt and end_dt per camera.
        Returns: [{camera_id, first_in, first_out, last_in, last_out}]
        """
        if not camera_ids:
            return []

        with connection.cursor() as cursor:
            cursor.execute("""
                WITH firsts AS (
                  SELECT DISTINCT ON (camera_id)
                         camera_id,
                         cc_in_count  AS first_in,
                         cc_out_count AS first_out,
                         created_at
                  FROM cross_counting_data_timeseries
                  WHERE camera_id = ANY(%s)
                    AND created_at >= %s
                    AND created_at <  %s
                  ORDER BY camera_id, created_at ASC
                ),
                lasts AS (
                  SELECT DISTINCT ON (camera_id)
                         camera_id,
                         cc_in_count  AS last_in,
                         cc_out_count AS last_out,
                         created_at
                  FROM cross_counting_data_timeseries
                  WHERE camera_id = ANY(%s)
                    AND created_at >= %s
                    AND created_at <  %s
                  ORDER BY camera_id, created_at DESC
                )
                SELECT COALESCE(l.camera_id, f.camera_id) AS camera_id,
                       f.first_in, f.first_out,
                       l.last_in,  l.last_out
                FROM lasts l
                FULL OUTER JOIN firsts f ON f.camera_id = l.camera_id
                ORDER BY camera_id;
            """, [camera_ids, start_dt, end_dt, camera_ids, start_dt, end_dt])

            rows = cursor.fetchall()
            out = []
            for row in rows:
                out.append({
                    "camera_id": row[0],
                    "first_in": row[1],
                    "first_out": row[2],
                    "last_in": row[3],
                    "last_out": row[4],
                })
            return out


# ------------------------------
# Data retention / volume
# ------------------------------
class DataRetentionManager:
    """Data retention & volume stats."""

    @staticmethod
    def get_data_volume_stats() -> Dict[str, Any]:
        from .models import CrossCountingData
        now = timezone.now()
        since_24h = now - timedelta(hours=24)
        since_7d = now - timedelta(days=7)

        total_records = CrossCountingData.objects.count()
        records_24h = CrossCountingData.objects.filter(created_at__gte=since_24h).count()
        records_7d = CrossCountingData.objects.filter(created_at__gte=since_7d).count()

        return {
            'total_records': total_records,
            'records_last_24h': records_24h,
            'records_last_7d': records_7d,
            'retention_status': 'healthy' if total_records > 0 else 'no_data'
        }
