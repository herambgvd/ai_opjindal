"""
Fixed Time-series utilities for CrossCountingData analytics
Optimized for high-frequency data analysis with PostgreSQL-specific features
ISSUE FIXED: Corrected cumulative max logic for past days and hour limiting for current day
"""

import logging
from collections import defaultdict
from datetime import timedelta, datetime, date
from typing import List, Dict, Any

from django.db import connection
from django.utils import timezone
from django.utils.timezone import localtime

logger = logging.getLogger(__name__)

def serialize_datetime_data(data):
    """
    Recursively serialize datetime and UUID objects in data structures to safe formats
    for JavaScript consumption
    """
    import uuid

    if isinstance(data, datetime):
        return data.isoformat()
    elif isinstance(data, date):
        return data.isoformat()
    elif isinstance(data, uuid.UUID):
        return str(data)  # Convert UUID to string
    elif isinstance(data, dict):
        return {key: serialize_datetime_data(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [serialize_datetime_data(item) for item in data]
    else:
        return data

class CrossCountingAnalytics:
    @staticmethod
    def refresh_materialized_views():
        """Refresh materialized views for dashboard queries"""
        with connection.cursor() as cursor:
            cursor.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY cross_counting_hourly_aggregates;")
            cursor.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY cross_counting_daily_peaks;")

    @staticmethod
    def get_camera_activity_summary(camera_ids: List[str], hours: int = 24) -> List[Dict[str, Any]]:
        """
        Get activity summary for multiple cameras over specified hours
        """
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

            columns = [col[0] for col in cursor.description] if cursor.description else []
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    @staticmethod
    def get_system_health_metrics(minutes: int = 60) -> Dict[str, Any]:
        """
        Get system health metrics for monitoring data ingestion
        """
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
            columns = [col[0] for col in cursor.description] if cursor.description else []
            return dict(zip(columns, row)) if row else {}

    @staticmethod
    def optimize_table_maintenance():
        """
        Perform maintenance operations for time-series table
        """
        with connection.cursor() as cursor:
            cursor.execute("ANALYZE cross_counting_data_timeseries;")

            cursor.execute("""
                SELECT 
                    pg_size_pretty(pg_total_relation_size('cross_counting_data_timeseries')) as total_size,
                    pg_size_pretty(pg_relation_size('cross_counting_data_timeseries')) as table_size,
                    pg_size_pretty(pg_indexes_size('cross_counting_data_timeseries')) as indexes_size
            """)

            columns = [col[0] for col in cursor.description] if cursor.description else []
            row = cursor.fetchone()
            return dict(zip(columns, row)) if row else {}

class TablePartitioningManager:
    """
    Utilities for managing table partitioning for very high volume data
    FIXED: Corrected cumulative max logic and hour limiting
    """

    @staticmethod
    def get_daily_analysis_data(region_id: int, date: date) -> Dict[str, Any]:
        """
        Updated daily analysis using simplified approach
        """
        from .models import Camera, CrossCountingData
        from django.db.models import Max

        cameras = Camera.objects.filter(region_id=region_id, status=True)

        if not cameras.exists():
            return {
                "cameras": [],
                "summary": {},
                "simplified_analysis": {"individual_camera_data": [], "regional_hourly_data": []}
            }

        print(f"FIXED DEBUG: Analysis for {date}")

        # Get traditional summary (peak cumulative counts)
        daily_data = []
        total_peak_in = 0
        total_peak_out = 0
        total_peak_total = 0

        for camera in cameras:
            daily_stats = CrossCountingData.objects.filter(
                camera=camera,
                created_at__date=date
            ).aggregate(
                peak_in_count=Max('cc_in_count'),
                peak_out_count=Max('cc_out_count'),
                peak_total_count=Max('cc_total_count')
            )

            if daily_stats['peak_in_count'] is not None:
                camera_data = {
                    "camera_name": camera.name,
                    "peak_in": daily_stats['peak_in_count'],
                    "peak_out": daily_stats['peak_out_count'],
                    "peak_total": daily_stats['peak_total_count']
                }
                daily_data.append(camera_data)
                total_peak_in += daily_stats['peak_in_count'] or 0
                total_peak_out += daily_stats['peak_out_count'] or 0
                total_peak_total += daily_stats['peak_total_count'] or 0

        # Get simplified analysis
        simplified_analysis = TablePartitioningManager.get_simplified_daily_analysis(region_id, date)

        print(f"FIXED DEBUG: Traditional summary - Cameras: {len(daily_data)}, Peak In: {total_peak_in}")
        print(f"FIXED DEBUG: Simplified analysis - Individual cameras: {len(simplified_analysis['individual_camera_data'])}")

        result = {
            "cameras": daily_data,
            "summary": {
                "total_peak_in": total_peak_in,
                "total_peak_out": total_peak_out,
                "total_peak_total": total_peak_total,
                "active_cameras": len(daily_data)
            },
            "simplified_analysis": simplified_analysis,
            "analysis_date": date,
            "analysis_type": "simplified_daily"
        }

        return serialize_datetime_data(result)

    @staticmethod
    def get_simplified_daily_analysis(region_id: int, target_date: date) -> Dict[str, Any]:
        """
        FIXED: Use Django ORM, cumulative max logic, proper date handling
        """
        from .models import Camera, CrossCountingData
        from django.db.models.functions import TruncHour

        local_tz = timezone.get_current_timezone()
        cameras = Camera.objects.filter(region_id=region_id, status=True)
        camera_ids = list(cameras.values_list('id', flat=True))

        if not camera_ids:
            return {
                "individual_camera_data": [],
                "regional_hourly_data": [],
                "region_name": "",
                "camera_count": 0
            }

        print(f"FIXED CUMULATIVE DEBUG: Analyzing data for {target_date}")
        print(f"FIXED CUMULATIVE DEBUG: Cameras: {len(camera_ids)}")

        # Fetch all data using ORM
        data_qs = CrossCountingData.objects.filter(
            camera_id__in=camera_ids,
            created_at__date=target_date
        ).order_by('camera_id', 'created_at')

        all_camera_data = list(
            data_qs.values('camera_id', 'cc_in_count', 'cc_out_count', 'cc_total_count', 'created_at'))

        print(f"FIXED CUMULATIVE DEBUG: Retrieved {len(all_camera_data)} total data points")

        if not all_camera_data:
            return {
                "individual_camera_data": [],
                "regional_hourly_data": [],
                "region_name": "",
                "camera_count": 0
            }

        # ULTRA-ROBUST FIX: Force historical analysis for any date that has complete 24-hour data
        max_data_hour = max(localtime(d['created_at']).hour for d in all_camera_data)

        # Get current time in the application's configured timezone
        now_aware = timezone.now()
        current_local = localtime(now_aware)
        current_date = current_local.date()
        current_hour = current_local.hour

        # If we have data spanning close to a full day (22+ hours), treat it as historical
        # This prevents timezone issues from limiting the analysis incorrectly
        has_near_full_day_data = max_data_hour >= 22
        is_clearly_historical = target_date < current_date
        is_current_date_but_has_full_data = (target_date == current_date and has_near_full_day_data)

        if is_clearly_historical or is_current_date_but_has_full_data:
            max_hour = max_data_hour  # Show all available data
            print(
                f"FIXED CUMULATIVE DEBUG: Historical/Complete day analysis - using all available hours up to: {max_hour}")
            if is_clearly_historical:
                print(f"FIXED CUMULATIVE DEBUG: Date is clearly in the past")
            if is_current_date_but_has_full_data:
                print(f"FIXED CUMULATIVE DEBUG: Current date but has near-complete day data ({max_data_hour}+ hours)")
        else:
            # Only limit for truly current/incomplete days
            max_hour = current_hour
            print(f"FIXED CUMULATIVE DEBUG: Current incomplete day - limiting to current hour: {max_hour}")

        print(f"FIXED CUMULATIVE DEBUG: Max hour: {max_hour}, Max data hour: {max_data_hour}")
        print(f"FIXED CUMULATIVE DEBUG: Current datetime: {now_aware} (hour {current_hour})")
        print(f"FIXED CUMULATIVE DEBUG: Current local date: {current_date}, Target date: {target_date}")
        print(f"FIXED CUMULATIVE DEBUG: Has near full day data: {has_near_full_day_data}")

        # Individual camera raw data
        individual_camera_data = []
        camera_objects = {cam.id: cam for cam in cameras}
        camera_data_points = defaultdict(list)
        for row in all_camera_data:
            created_at_local = localtime(row['created_at'])
            if created_at_local.hour > max_hour:
                continue
            camera_data_points[row['camera_id']].append({
                'cc_in_count': row['cc_in_count'],
                'cc_out_count': row['cc_out_count'],
                'cc_total_count': row['cc_total_count'],
                'created_at': created_at_local.strftime('%H:%M:%S'),
                'timestamp': created_at_local
            })

        for camera_id in camera_ids:
            if camera_id in camera_objects and camera_id in camera_data_points:
                data_points = camera_data_points[camera_id]
                individual_camera_data.append({
                    'camera_id': str(camera_id),
                    'camera_name': camera_objects[camera_id].name,
                    'data_points': data_points,
                    'total_points': len(data_points),
                    'first_time': data_points[0]['created_at'] if data_points else '',
                    'last_time': data_points[-1]['created_at'] if data_points else '',
                    'max_in': max([p['cc_in_count'] for p in data_points], default=0),
                    'max_out': max([p['cc_out_count'] for p in data_points], default=0)
                })

        print(f"FIXED CUMULATIVE DEBUG: Individual camera data prepared for {len(individual_camera_data)} cameras")

        # Group for hourly max
        camera_hour_data = defaultdict(lambda: defaultdict(list))
        for row in all_camera_data:
            created_at_local = localtime(row['created_at'])
            hour = created_at_local.hour
            if hour > max_hour:
                continue
            camera_hour_data[row['camera_id']][hour].append({
                'cc_in_count': row['cc_in_count'],
                'cc_out_count': row['cc_out_count'],
                'created_at': created_at_local
            })

        # Cumulative max per camera
        camera_hourly_values = {}
        for camera_id in camera_ids:
            if camera_id not in camera_objects:
                continue
            camera_name = camera_objects[camera_id].name
            camera_hourly_values[camera_id] = {}
            cumulative_in = 0
            cumulative_out = 0
            print(f"FIXED CUMULATIVE DEBUG: Processing {camera_name}")
            for hour in range(max_hour + 1):
                if hour in camera_hour_data[camera_id]:
                    hour_records = camera_hour_data[camera_id][hour]
                    hour_max_in = max(record['cc_in_count'] for record in hour_records)
                    hour_max_out = max(record['cc_out_count'] for record in hour_records)
                    cumulative_in = max(cumulative_in, hour_max_in)
                    cumulative_out = max(cumulative_out, hour_max_out)
                    print(f"FIXED CUMULATIVE DEBUG:   Hour {hour}: In={cumulative_in}, Out={cumulative_out} (updated)")
                else:
                    if cumulative_in > 0 or cumulative_out > 0:
                        print(
                            f"FIXED CUMULATIVE DEBUG:   Hour {hour}: In={cumulative_in}, Out={cumulative_out} (carried forward)")
                camera_hourly_values[camera_id][hour] = {
                    'cc_in_count': cumulative_in,
                    'cc_out_count': cumulative_out
                }

        # Regional totals
        regional_hourly_data = []
        for hour in range(max_hour + 1):
            total_in = 0
            total_out = 0
            active_cameras = 0
            for camera_id in camera_ids:
                if camera_id in camera_hourly_values:
                    values = camera_hourly_values[camera_id][hour]
                    total_in += values['cc_in_count']
                    total_out += values['cc_out_count']
                    if values['cc_in_count'] > 0 or values['cc_out_count'] > 0:
                        active_cameras += 1
            regional_hourly_data.append({
                'hour': hour,
                'total_in_count': total_in,
                'total_out_count': total_out,
                'active_cameras': active_cameras
            })

        # Debug regional
        non_zero_hours = [h for h in regional_hourly_data if h['total_in_count'] > 0 or h['total_out_count'] > 0]
        if non_zero_hours:
            print(f"FIXED CUMULATIVE DEBUG: Regional data spans hours: {[h['hour'] for h in non_zero_hours]}")
            for h in non_zero_hours:
                print(f"FIXED CUMULATIVE DEBUG: Hour {h['hour']}: In={h['total_in_count']}, Out={h['total_out_count']}")

        region_name = cameras.first().region.name if cameras.exists() else ""

        result = {
            "individual_camera_data": individual_camera_data,
            "regional_hourly_data": regional_hourly_data,
            "region_name": region_name,
            "camera_count": len(camera_ids),
            "analysis_type": "cumulative_max_carry_forward_no_occupancy",
            "target_date": target_date.strftime('%Y-%m-%d')
        }

        return serialize_datetime_data(result)

    @staticmethod
    def get_comparative_analysis_data(region_id: int, base_date: date, compare_date: date) -> Dict[str, Any]:
        """
        Get comparative analysis between two dates for a region
        """
        base_data = TablePartitioningManager.get_daily_analysis_data(region_id, base_date)
        compare_data = TablePartitioningManager.get_daily_analysis_data(region_id, compare_date)

        print(f"FIXED DEBUG: Comparative analysis for {base_date} vs {compare_date}")
        print(f"FIXED DEBUG: Base data cameras: {len(base_data.get('cameras', []))}")
        print(f"FIXED DEBUG: Compare data cameras: {len(compare_data.get('cameras', []))}")

        comparison = []
        for base_camera in base_data["cameras"]:
            compare_camera = next(
                (c for c in compare_data["cameras"] if c["camera_name"] == base_camera["camera_name"]),
                {"peak_in": 0, "peak_out": 0, "peak_total": 0}
            )

            comparison.append({
                "camera_name": base_camera["camera_name"],
                "base_in": base_camera["peak_in"],
                "base_out": base_camera["peak_out"],
                "base_total": base_camera["peak_total"],
                "compare_in": compare_camera["peak_in"],
                "compare_out": compare_camera["peak_out"],
                "compare_total": compare_camera["peak_total"],
                "diff_in": compare_camera["peak_in"] - base_camera["peak_in"],
                "diff_out": compare_camera["peak_out"] - base_camera["peak_out"],
                "diff_total": compare_camera["peak_total"] - base_camera["peak_total"]
            })

        print(f"FIXED DEBUG: Total base: {sum(c['base_total'] for c in comparison)}, Total compare: {sum(c['compare_total'] for c in comparison)}, Difference: {sum(c['compare_total'] for c in comparison) - sum(c['base_total'] for c in comparison)}")

        result = {
            "base_date": base_date,
            "compare_date": compare_date,
            "comparison": comparison,
            "base_summary": base_data["summary"],
            "compare_summary": compare_data["summary"],
            "base_hourly_aggregates": base_data.get("simplified_analysis", {}).get("regional_hourly_data", []),
            "compare_hourly_aggregates": compare_data.get("simplified_analysis", {}).get("regional_hourly_data", [])
        }

        return serialize_datetime_data(result)

    @staticmethod
    def get_comprehensive_analysis_data(region_id: int, from_date: date, to_date: date) -> Dict[str, Any]:
        """
        Get comprehensive analysis for a date range (max 7 days) using created_at
        """
        from .models import Camera, CrossCountingData
        from django.db.models import Max
        from django.db.models.functions import TruncDate

        cameras = Camera.objects.filter(region_id=region_id, status=True)
        daily_trends = []

        print(f"FIXED DEBUG: Comprehensive analysis from {from_date} to {to_date}")

        for camera in cameras:
            daily_data = CrossCountingData.objects.filter(
                camera=camera,
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
                "camera_name": camera.name,
                "daily_data": list(daily_data)
            })

        total_days = (to_date - from_date).days + 1
        region_hourly_aggregates = TablePartitioningManager.get_simplified_daily_analysis(region_id, from_date)

        print(f"FIXED DEBUG: Analyzed {len(cameras)} cameras over {total_days} days")
        print(f"FIXED DEBUG: Total daily data points: {sum(len(trend['daily_data']) for trend in daily_trends)}")

        result = {
            "from_date": from_date,
            "to_date": to_date,
            "total_days": total_days,
            "daily_trends": daily_trends,
            "cameras": [{"id": str(cam.id), "name": cam.name} for cam in cameras],
            "region_hourly_aggregates": region_hourly_aggregates
        }

        return serialize_datetime_data(result)

    @staticmethod
    def get_hourly_region_aggregates(region_id: int, start_time, end_time) -> Dict[str, Any]:
        """
        Get hourly aggregated In/Out counts for all cameras in a region
        """
        from .models import Camera

        cameras = Camera.objects.filter(region_id=region_id, status=True)
        camera_ids = list(cameras.values_list('id', flat=True))

        if not camera_ids:
            return {
                "hourly_data": [{"hour": h, "total_in_count": 0, "total_out_count": 0} for h in range(24)],
                "region_name": "",
                "camera_count": 0,
                "individual_camera_data": []
            }

        if start_time.tzinfo is None:
            start_time = timezone.make_aware(start_time)
        if end_time.tzinfo is None:
            end_time = timezone.make_aware(end_time)

        print(f"FIXED DEBUG: Querying hourly data from {start_time} to {end_time}")
        print(f"FIXED DEBUG: Camera count: {len(camera_ids)}")

        with connection.cursor() as cursor:
            cursor.execute("""
                WITH ranked_data AS (
                    SELECT camera_id,
                           cc_in_count,
                           cc_out_count,
                           EXTRACT(HOUR FROM created_at) as hour,
                           created_at,
                           ROW_NUMBER() OVER (
                               PARTITION BY camera_id, EXTRACT(HOUR FROM created_at)
                               ORDER BY created_at DESC
                           ) as rn
                    FROM cross_counting_data_timeseries
                    WHERE camera_id = ANY (%s)
                      AND created_at >= %s
                      AND created_at < %s
                ),
                last_values_per_hour AS (
                    SELECT camera_id, hour, cc_in_count, cc_out_count
                    FROM ranked_data
                    WHERE rn = 1
                ),
                region_hourly_totals AS (
                    SELECT hour, SUM(cc_in_count) as total_in_count, SUM(cc_out_count) as total_out_count
                    FROM last_values_per_hour
                    GROUP BY hour
                ),
                all_hours AS (
                    SELECT generate_series(0, 23) as hour
                )
                SELECT ah.hour,
                       COALESCE(rht.total_in_count, 0) as total_in_count,
                       COALESCE(rht.total_out_count, 0) as total_out_count
                FROM all_hours ah
                LEFT JOIN region_hourly_totals rht ON ah.hour = rht.hour
                ORDER BY ah.hour
            """, [camera_ids, start_time, end_time])

            hourly_data = []
            for row in cursor.fetchall():
                hourly_data.append({
                    'hour': int(row[0]),
                    'total_in_count': int(row[1]),
                    'total_out_count': int(row[2])
                })

        non_zero_hours = [h for h in hourly_data if h['total_in_count'] > 0 or h['total_out_count'] > 0]
        if non_zero_hours:
            print(f"FIXED DEBUG: Found data for hours: {[h['hour'] for h in non_zero_hours]}")
            print(f"FIXED DEBUG: Last hour with data: {max([h['hour'] for h in non_zero_hours])}")
            for h in non_zero_hours[:5]:
                print(f"FIXED DEBUG: Hour {h['hour']}: In={h['total_in_count']}, Out={h['total_out_count']}")

        individual_camera_data = []
        camera_objects = {cam.id: cam for cam in cameras}

        with connection.cursor() as cursor:
            cursor.execute("""
                WITH ranked_camera_data AS (
                    SELECT camera_id,
                           cc_in_count,
                           cc_out_count,
                           EXTRACT(HOUR FROM created_at) as hour,
                           created_at,
                           ROW_NUMBER() OVER (
                               PARTITION BY camera_id, EXTRACT(HOUR FROM created_at)
                               ORDER BY created_at DESC
                           ) as rn
                    FROM cross_counting_data_timeseries
                    WHERE camera_id = ANY (%s)
                      AND created_at >= %s
                      AND created_at < %s
                ),
                camera_last_values AS (
                    SELECT camera_id, hour, cc_in_count, cc_out_count
                    FROM ranked_camera_data
                    WHERE rn = 1
                ),
                all_hours AS (
                    SELECT generate_series(0, 23) as hour
                ),
                all_cameras AS (
                    SELECT unnest(%s::uuid[]) as camera_id
                )
                SELECT ac.camera_id,
                       ah.hour,
                       COALESCE(clv.cc_in_count, 0) as cc_in_count,
                       COALESCE(clv.cc_out_count, 0) as cc_out_count
                FROM all_cameras ac
                CROSS JOIN all_hours ah
                LEFT JOIN camera_last_values clv
                    ON ac.camera_id = clv.camera_id AND ah.hour = clv.hour
                ORDER BY ac.camera_id, ah.hour
            """, [camera_ids, start_time, end_time, camera_ids])

            camera_data_dict = defaultdict(list)
            for row in cursor.fetchall():
                camera_id = row[0]
                hour = int(row[1])
                cc_in_count = int(row[2])
                cc_out_count = int(row[3])
                camera_data_dict[camera_id].append({
                    'hour': hour,
                    'cc_in_count': cc_in_count,
                    'cc_out_count': cc_out_count
                })

            for camera_id in camera_ids:
                if camera_id in camera_objects:
                    individual_camera_data.append({
                        'camera_id': str(camera_id),
                        'camera_name': camera_objects[camera_id].name,
                        'hourly_data': camera_data_dict[camera_id]
                    })

        region_name = cameras.first().region.name if cameras.exists() else ""

        result = {
            "hourly_data": hourly_data,
            "region_name": region_name,
            "camera_count": len(camera_ids),
            "individual_camera_data": individual_camera_data
        }

        return serialize_datetime_data(result)

    @staticmethod
    def get_current_occupancy_data() -> List[Dict[str, Any]]:
        """
        Get current occupancy percentage for all regions for public display.
        Uses multiple calculation methods for more accurate occupancy estimation.

        Methods used:
        1. Simple In-Out difference (traditional)
        2. Weighted average based on camera activity
        3. Historical baseline comparison
        4. Activity-based occupancy estimation
        """
        from .models import Region, Camera, CrossCountingData
        from django.utils import timezone
        from datetime import timedelta
        from django.db.models import Avg, Max, Min, Count

        regions = Region.objects.all()
        occupancy_data = []

        for region in regions:
            cameras = Camera.objects.filter(region=region, status=True)
            if not cameras.exists():
                occupancy_data.append({
                    "region_name": region.name,
                    "current_count": 0,
                    "max_occupancy": region.occupancy,
                    "occupancy_percentage": 0.0,
                    "total_in_count": 0,
                    "total_out_count": 0,
                    "occupancy_by_in_out": 0,
                    "smart_occupancy": 0,
                    "calculation_method": "no_cameras",
                    "confidence_score": 0.0
                })
                continue

            # Get current data for all cameras
            now = timezone.now()
            current_hour = now.hour

            total_in_count = 0
            total_out_count = 0
            camera_data = []

            for camera in cameras:
                latest_data = CrossCountingData.objects.filter(
                    camera=camera
                ).order_by('-created_at').first()
                if latest_data:
                    total_in_count += latest_data.cc_in_count
                    total_out_count += latest_data.cc_out_count
                    camera_data.append({
                        'camera': camera,
                        'in_count': latest_data.cc_in_count,
                        'out_count': latest_data.cc_out_count,
                        'timestamp': latest_data.created_at
                    })

            # Method 1: Traditional In-Out difference
            occupancy_by_in_out = max(0, total_in_count - total_out_count)

            # Method 2: Smart occupancy calculation
            smart_occupancy, method_used, confidence = TablePartitioningManager._calculate_smart_occupancy(
                region, cameras, camera_data, now
            )

            # Use smart occupancy as primary, fallback to traditional
            final_occupancy = smart_occupancy if confidence > 0.3 else occupancy_by_in_out

            # Cap current_count at max_occupancy for display
            current_count = min(final_occupancy, region.occupancy)
            occupancy_percentage = (current_count / region.occupancy * 100) if region.occupancy > 0 else 0.0
            occupancy_percentage = min(occupancy_percentage, 100.0)

            occupancy_data.append({
                "region_name": region.name,
                "current_count": int(current_count),
                "max_occupancy": region.occupancy,
                "occupancy_percentage": round(occupancy_percentage, 1),
                "total_in_count": total_in_count,
                "total_out_count": total_out_count,
                "occupancy_by_in_out": occupancy_by_in_out,
                "smart_occupancy": int(smart_occupancy),
                "calculation_method": method_used,
                "confidence_score": round(confidence, 2),
                "available_count": max(0, region.occupancy - int(current_count))
            })

        return occupancy_data

    @staticmethod
    def _calculate_smart_occupancy(region, cameras, camera_data, current_time):
        """
        Calculate smart occupancy using multiple methods and return the best estimate.

        Returns: (occupancy_estimate, method_used, confidence_score)
        """
        from django.db.models import Avg, Max, Count
        from datetime import timedelta

        if not camera_data:
            return 0, "no_data", 0.0

        # Method 1: Enhanced In-Out with error correction
        total_in = sum(c['in_count'] for c in camera_data)
        total_out = sum(c['out_count'] for c in camera_data)
        basic_occupancy = max(0, total_in - total_out)

        # Method 2: Historical pattern analysis
        historical_occupancy = TablePartitioningManager._get_historical_baseline_occupancy(
            region, current_time, cameras
        )

        # Method 3: Activity-based estimation
        activity_occupancy = TablePartitioningManager._get_activity_based_occupancy(
            region, camera_data, current_time
        )

        # Method 4: Weighted camera analysis
        weighted_occupancy = TablePartitioningManager._get_weighted_camera_occupancy(
            camera_data, region.occupancy
        )

        # Calculate confidence scores for each method
        methods = [
            ("basic_in_out", basic_occupancy, 0.6 if total_in > 0 else 0.1),
            ("historical_pattern", historical_occupancy, 0.7 if historical_occupancy > 0 else 0.2),
            ("activity_based", activity_occupancy, 0.8 if activity_occupancy > 0 else 0.3),
            ("weighted_cameras", weighted_occupancy, 0.7 if len(camera_data) > 1 else 0.4)
        ]

        # Filter out methods with very low confidence
        valid_methods = [(name, value, conf) for name, value, conf in methods if conf > 0.2]

        if not valid_methods:
            return basic_occupancy, "basic_fallback", 0.1

        # Weighted average of all valid methods
        total_weight = sum(conf for _, _, conf in valid_methods)
        if total_weight > 0:
            weighted_average = sum(value * conf for _, value, conf in valid_methods) / total_weight
            best_method = max(valid_methods, key=lambda x: x[2])
            return int(weighted_average), f"hybrid_{best_method[0]}", min(0.9, total_weight / len(valid_methods))

        return basic_occupancy, "basic_fallback", 0.3

    @staticmethod
    def _get_historical_baseline_occupancy(region, current_time, cameras):
        """
        Calculate expected occupancy based on historical patterns for the same time.
        """
        from datetime import timedelta
        from django.db.models import Avg, Max

        try:
            # Look at same hour for last 7 days
            current_hour = current_time.hour
            week_ago = current_time - timedelta(days=7)

            # Get historical data for the same hour over past week
            historical_data = []
            for days_back in range(1, 8):  # Last 7 days
                check_date = (current_time - timedelta(days=days_back)).date()
                day_data = CrossCountingData.objects.filter(
                    camera__in=cameras,
                    created_at__date=check_date,
                    created_at__hour=current_hour
                ).aggregate(
                    max_in=Max('cc_in_count'),
                    max_out=Max('cc_out_count')
                )

                if day_data['max_in'] and day_data['max_out']:
                    day_occupancy = max(0, day_data['max_in'] - day_data['max_out'])
                    historical_data.append(day_occupancy)

            if historical_data:
                # Return average of historical occupancy, weighted toward recent days
                weights = [0.3, 0.25, 0.2, 0.15, 0.1, 0.05, 0.05]  # More weight to recent days
                if len(historical_data) == len(weights):
                    return sum(val * weight for val, weight in zip(historical_data, weights))
                else:
                    return sum(historical_data) / len(historical_data)

            return 0
        except Exception:
            return 0

    @staticmethod
    def _get_activity_based_occupancy(region, camera_data, current_time):
        """
        Estimate occupancy based on recent activity patterns.
        """
        from datetime import timedelta

        try:
            if not camera_data:
                return 0

            # Check if there's recent activity (last 30 minutes)
            recent_threshold = current_time - timedelta(minutes=30)
            active_cameras = 0
            total_recent_activity = 0

            for cam_data in camera_data:
                if cam_data['timestamp'] > recent_threshold:
                    active_cameras += 1
                    # Consider any in/out counts as activity indicators
                    activity_score = min(cam_data['in_count'] + cam_data['out_count'], region.occupancy // len(camera_data))
                    total_recent_activity += activity_score

            # If no cameras have recent data, assume some baseline occupancy
            if active_cameras == 0:
                return 0

            # Scale activity to reasonable occupancy estimate
            activity_factor = active_cameras / len(camera_data)
            estimated_occupancy = min(total_recent_activity * activity_factor, region.occupancy * 0.8)

            return max(0, int(estimated_occupancy))

        except Exception:
            return 0

    @staticmethod
    def _get_weighted_camera_occupancy(camera_data, max_occupancy):
        """
        Calculate occupancy using weighted average of camera in-out differences.
        """
        try:
            if not camera_data:
                return 0

            # Calculate individual camera occupancies
            camera_occupancies = []
            for cam_data in camera_data:
                cam_occupancy = max(0, cam_data['in_count'] - cam_data['out_count'])
                # Weight based on total activity (cameras with more activity are more reliable)
                activity_weight = min(1.0, (cam_data['in_count'] + cam_data['out_count']) / 10)
                activity_weight = max(0.1, activity_weight)  # Minimum weight

                camera_occupancies.append((cam_occupancy, activity_weight))

            # Calculate weighted average
            total_weight = sum(weight for _, weight in camera_occupancies)
            if total_weight > 0:
                weighted_avg = sum(occ * weight for occ, weight in camera_occupancies) / total_weight
                return min(int(weighted_avg), max_occupancy)

            return 0

        except Exception:
            return 0
```

