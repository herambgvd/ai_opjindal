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

        # FIXED: Determine max_hour properly
        current_date = timezone.now().date()
        current_local = localtime(timezone.now())
        max_data_hour = max(localtime(d['created_at']).hour for d in all_camera_data)

        # Only limit to current hour if target_date is TODAY (not yesterday)
        if target_date == current_date:
            max_hour = current_local.hour
            print(f"FIXED CUMULATIVE DEBUG: Today's analysis - limiting to current hour: {max_hour}")
        else:
            max_hour = max_data_hour
            print(f"FIXED CUMULATIVE DEBUG: Historical analysis - using all available hours up to: {max_hour}")

        print(
            f"FIXED CUMULATIVE DEBUG: Max hour: {max_hour}, Max data hour: {max_data_hour}, Current date: {current_date}, Target date: {target_date}")

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
        Get current occupancy percentage for all regions for public display
        """
        from .models import Region, Camera, CrossCountingData
        from django.utils import timezone
        from datetime import timedelta

        regions = Region.objects.all()
        occupancy_data = []

        for region in regions:
            cameras = Camera.objects.filter(region=region, status=True)
            if not cameras.exists():
                occupancy_data.append({
                    "region_name": region.name,
                    "current_count": 0,
                    "max_occupancy": region.occupancy,
                    "occupancy_percentage": 0.0
                })
                continue

            current_total = 0
            recent_time = timezone.now() - timedelta(minutes=5)

            for camera in cameras:
                latest_data = CrossCountingData.objects.filter(
                    camera=camera,
                    created_at__gte=recent_time
                ).order_by('-created_at').first()

                if latest_data:
                    camera_occupancy = max(0, latest_data.cc_in_count - latest_data.cc_out_count)
                    current_total += camera_occupancy

            occupancy_percentage = (current_total / region.occupancy * 100) if region.occupancy > 0 else 0.0
            occupancy_percentage = min(occupancy_percentage, 100.0)

            occupancy_data.append({
                "region_name": region.name,
                "current_count": current_total,
                "max_occupancy": region.occupancy,
                "occupancy_percentage": round(occupancy_percentage, 1)
            })

        return occupancy_data

    @staticmethod
    def get_dashboard_statistics() -> Dict[str, Any]:
        """
        Get comprehensive platform statistics for dashboard
        """
        from .models import Region, Camera, CrossCountingData
        from django.utils import timezone
        from datetime import timedelta

        total_regions = Region.objects.count()
        total_cameras = Camera.objects.count()
        active_cameras = Camera.objects.filter(status=True).count()

        since_24h = timezone.now() - timedelta(hours=24)
        recent_data_points = CrossCountingData.objects.filter(
            created_at__gte=since_24h
        ).count()

        health_metrics = CrossCountingAnalytics.get_system_health_metrics(minutes=60)
        volume_stats = DataRetentionManager.get_data_volume_stats()
        occupancy_data = TablePartitioningManager.get_current_occupancy_data()
        total_current_occupancy = sum(item['current_count'] for item in occupancy_data)
        total_max_occupancy = sum(item['max_occupancy'] for item in occupancy_data)
        avg_occupancy_percentage = (
            total_current_occupancy / total_max_occupancy * 100) if total_max_occupancy > 0 else 0.0

        return {
            "basic_stats": {
                "total_regions": total_regions,
                "total_cameras": total_cameras,
                "active_cameras": active_cameras,
                "inactive_cameras": total_cameras - active_cameras
            },
            "activity_stats": {
                "recent_data_points_24h": recent_data_points,
                "avg_data_points_per_hour": recent_data_points / 24 if recent_data_points > 0 else 0
            },
            "system_health": health_metrics,
            "data_volume": volume_stats,
            "occupancy_summary": {
                "total_current_occupancy": total_current_occupancy,
                "total_max_occupancy": total_max_occupancy,
                "avg_occupancy_percentage": round(avg_occupancy_percentage, 1),
                "regions_data": occupancy_data
            }
        }

    @staticmethod
    def get_enhanced_dashboard_data() -> List[Dict[str, Any]]:
        """
        Get region cards data with cameras and their latest counts
        """
        from .models import Region, Camera, CrossCountingData
        from django.utils import timezone
        from datetime import timedelta

        regions = Region.objects.prefetch_related('cameras').all()
        enhanced_data = []
        recent_time = timezone.now() - timedelta(minutes=5)

        for region in regions:
            cameras = Camera.objects.filter(region=region, status=True)
            camera_data = []
            region_total_in = 0
            region_total_out = 0
            region_current_occupancy = 0

            for camera in cameras:
                latest_data = CrossCountingData.objects.filter(
                    camera=camera,
                    created_at__gte=recent_time
                ).order_by('-created_at').first()

                if latest_data:
                    camera_occupancy = max(0, latest_data.cc_in_count - latest_data.cc_out_count)
                    camera_info = {
                        'name': camera.name,
                        'latest_in_count': latest_data.cc_in_count,
                        'latest_out_count': latest_data.cc_out_count,
                        'current_occupancy': camera_occupancy,
                        'last_updated': latest_data.created_at,
                        'status': 'active'
                    }
                    region_total_in += latest_data.cc_in_count
                    region_total_out += latest_data.cc_out_count
                    region_current_occupancy += camera_occupancy
                else:
                    camera_info = {
                        'name': camera.name,
                        'latest_in_count': 0,
                        'latest_out_count': 0,
                        'current_occupancy': 0,
                        'last_updated': None,
                        'status': 'no_data'
                    }

                camera_data.append(camera_info)

            occupancy_percentage = (region_current_occupancy / region.occupancy * 100) if region.occupancy > 0 else 0.0

            enhanced_data.append({
                'region_name': region.name,
                'region_id': region.id,
                'max_occupancy': region.occupancy,
                'current_occupancy': region_current_occupancy,
                'occupancy_percentage': round(occupancy_percentage, 1),
                'total_in_count': region_total_in,
                'total_out_count': region_total_out,
                'cameras': camera_data,
                'camera_count': len(camera_data)
            })

        return enhanced_data

class DataRetentionManager:
    @staticmethod
    def cleanup_old_data(days_to_keep: int = 90) -> int:
        """
        Remove data older than specified days
        """
        from .models import CrossCountingData
        from django.utils import timezone
        from datetime import timedelta

        cutoff_date = timezone.now() - timedelta(days=days_to_keep)
        batch_size = 10000
        total_deleted = 0

        while True:
            deleted_count = CrossCountingData.objects.filter(
                created_at__lt=cutoff_date
            )[:batch_size].delete()[0]
            total_deleted += deleted_count
            if deleted_count < batch_size:
                break

        return total_deleted

    @staticmethod
    def get_data_volume_stats() -> Dict[str, Any]:
        """
        Get statistics about data volume for capacity planning
        """
        from .models import CrossCountingData
        from django.db.models import Count, Min, Max
        from django.db.models.functions import TruncDate

        total_records = CrossCountingData.objects.count()

        if total_records == 0:
            return {"total_records": 0, "daily_stats": []}

        date_range = CrossCountingData.objects.aggregate(
            min_date=Min('created_at'),
            max_date=Max('created_at')
        )

        daily_stats = CrossCountingData.objects.annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            record_count=Count('id')
        ).order_by('-date')[:30]

        return {
            "total_records": total_records,
            "date_range": date_range,
            "daily_stats": list(daily_stats),
            "avg_daily_records": total_records / max(1, (date_range['max_date'] - date_range['min_date']).days) if
            date_range['max_date'] and date_range['min_date'] else 0
        }

class TrafficFlowAnalyzer:
    @staticmethod
    def get_traffic_flow_analysis(camera_id: str, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        """
        Analyze traffic flow patterns with entry/exit calculations
        """
        with connection.cursor() as cursor:
            cursor.execute("""
                WITH daily_resets AS (
                    SELECT DATE(created_at) as date,
                           MAX(cc_in_count) as daily_max_in,
                           MAX(cc_out_count) as daily_max_out,
                           MAX(cc_total_count) as daily_max_total,
                           MIN(cc_in_count) as daily_min_in,
                           MIN(cc_out_count) as daily_min_out,
                           COUNT(*) as data_points
                    FROM cross_counting_data_timeseries
                    WHERE camera_id = %s
                      AND created_at BETWEEN %s AND %s
                    GROUP BY DATE(created_at)
                )
                SELECT date,
                       daily_max_in - daily_min_in as net_entries,
                       daily_max_out - daily_min_out as net_exits,
                       daily_max_total - daily_min_in as net_total,
                       daily_max_in,
                       daily_max_out,
                       daily_max_total,
                       data_points
                FROM daily_resets
                ORDER BY date
            """, [camera_id, start_time, end_time])

            columns = [col[0] for col in cursor.description] if cursor.description else []
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    @staticmethod
    def get_peak_hours_analysis(region_id: int, date_range: tuple) -> Dict[str, Any]:
        """
        Analyze peak hours across date range
        """
        start_date, end_date = date_range

        with connection.cursor() as cursor:
            cursor.execute("""
                WITH hourly_totals AS (
                    SELECT EXTRACT(HOUR FROM ccd.created_at) as hour,
                           AVG(ccd.cc_total_count) as avg_total,
                           MAX(ccd.cc_total_count) as max_total,
                           COUNT(*) as data_points
                    FROM cross_counting_data_timeseries ccd
                    JOIN cross_counting_camera c ON ccd.camera_id = c.id
                    WHERE c.region_id = %s
                      AND c.status = true
                      AND DATE(ccd.created_at) BETWEEN %s AND %s
                    GROUP BY EXTRACT(HOUR FROM ccd.created_at)
                )
                SELECT hour,
                       ROUND(avg_total::numeric, 2) as avg_total,
                       max_total,
                       data_points
                FROM hourly_totals
                ORDER BY hour
            """, [region_id, start_date, end_date])

            columns = [col[0] for col in cursor.description] if cursor.description else []
            hourly_data = [dict(zip(columns, row)) for row in cursor.fetchall()]
            peak_hour = max(hourly_data, key=lambda x: x['avg_total']) if hourly_data else None

            return {
                "hourly_data": hourly_data,
                "peak_hour": peak_hour,
                "analysis_period": f"{start_date} to {end_date}"
            }

class OccupancyAnalyzer:
    @staticmethod
    def get_real_time_occupancy(region_id: int = None) -> Dict[str, Any]:
        """
        Get real-time occupancy for all regions or specific region
        """
        from .models import Region, Camera, CrossCountingData
        from django.utils import timezone
        from datetime import timedelta

        recent_time = timezone.now() - timedelta(minutes=5)
        regions = Region.objects.filter(id=region_id) if region_id else Region.objects.all()
        occupancy_data = []

        for region in regions:
            cameras = Camera.objects.filter(region=region, status=True)
            region_occupancy = 0
            camera_details = []

            for camera in cameras:
                latest_data = CrossCountingData.objects.filter(
                    camera=camera,
                    created_at__gte=recent_time
                ).order_by('-created_at').first()

                if latest_data:
                    camera_occupancy = max(0, latest_data.cc_in_count - latest_data.cc_out_count)
                    region_occupancy += camera_occupancy
                    camera_details.append({
                        'camera_name': camera.name,
                        'current_occupancy': camera_occupancy,
                        'last_in': latest_data.cc_in_count,
                        'last_out': latest_data.cc_out_count,
                        'last_updated': latest_data.created_at
                    })
                else:
                    camera_details.append({
                        'camera_name': camera.name,
                        'current_occupancy': 0,
                        'last_in': 0,
                        'last_out': 0,
                        'last_updated': None
                    })

            occupancy_percentage = (region_occupancy / region.occupancy * 100) if region.occupancy > 0 else 0.0
            occupancy_data.append({
                'region_name': region.name,
                'region_id': region.id,
                'current_occupancy': region_occupancy,
                'max_occupancy': region.occupancy,
                'occupancy_percentage': round(occupancy_percentage, 1),
                'cameras': camera_details,
                'status': 'normal' if occupancy_percentage < 80 else 'high' if occupancy_percentage < 100 else 'overcapacity'
            })

        return {
            'regions': occupancy_data,
            'timestamp': timezone.now(),
            'total_regions': len(occupancy_data)
        }

    @staticmethod
    def get_occupancy_trends(region_id: int, hours: int = 24) -> Dict[str, Any]:
        """
        Get occupancy trends over specified hours
        """
        from .models import Camera
        from django.utils import timezone
        from datetime import timedelta

        end_time = timezone.now()
        start_time = end_time - timedelta(hours=hours)
        cameras = Camera.objects.filter(region_id=region_id, status=True)
        camera_ids = list(cameras.values_list('id', flat=True))

        if not camera_ids:
            return {'hourly_occupancy': [], 'camera_trends': []}

        with connection.cursor() as cursor:
            cursor.execute("""
                WITH hourly_last_values AS (
                    SELECT camera_id,
                           DATE_TRUNC('hour', created_at) as hour_bucket,
                           cc_in_count,
                           cc_out_count,
                           ROW_NUMBER() OVER (
                               PARTITION BY camera_id, DATE_TRUNC('hour', created_at)
                               ORDER BY created_at DESC
                           ) as rn
                    FROM cross_counting_data_timeseries
                    WHERE camera_id = ANY (%s)
                      AND created_at BETWEEN %s AND %s
                ),
                camera_hourly_occupancy AS (
                    SELECT camera_id,
                           hour_bucket,
                           GREATEST(0, cc_in_count - cc_out_count) as occupancy
                    FROM hourly_last_values
                    WHERE rn = 1
                )
                SELECT hour_bucket,
                       SUM(occupancy) as total_occupancy,
                       COUNT(DISTINCT camera_id) as active_cameras
                FROM camera_hourly_occupancy
                GROUP BY hour_bucket
                ORDER BY hour_bucket
            """, [camera_ids, start_time, end_time])

            hourly_data = []
            for row in cursor.fetchall():
                hourly_data.append({
                    'hour': row[0],
                    'total_occupancy': int(row[1]),
                    'active_cameras': int(row[2])
                })

        return {
            'hourly_occupancy': hourly_data,
            'analysis_period': f"{start_time} to {end_time}",
            'region_id': region_id
        }

class PerformanceOptimizer:
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
            size_info = dict(zip(columns, row)) if row else {}

            cursor.execute("""
                SELECT indexname,
                       idx_scan as times_used,
                       idx_tup_read as tuples_read,
                       idx_tup_fetch as tuples_fetched
                FROM pg_stat_user_indexes
                WHERE relname = 'cross_counting_data_timeseries'
                ORDER BY idx_scan DESC
            """)

            index_stats = []
            for row in cursor.fetchall():
                index_stats.append({
                    'index_name': row[0],
                    'times_used': row[1],
                    'tuples_read': row[2],
                    'tuples_fetched': row[3]
                })

            return {
                'size_info': size_info,
                'index_statistics': index_stats,
                'maintenance_completed': timezone.now()
            }

def get_timezone_aware_now():
    """Get current time in the application timezone"""
    return timezone.now()

def convert_to_local_time(dt):
    """Convert datetime to local timezone if needed"""
    from django.utils import timezone
    if dt.tzinfo is None:
        return timezone.make_aware(dt)
    return dt

def validate_date_range(start_date, end_date, max_days=30):
    """Validate date range for analytics queries"""
    if start_date > end_date:
        raise ValueError("Start date must be before end date")
    if (end_date - start_date).days > max_days:
        raise ValueError(f"Date range cannot exceed {max_days} days")
    if end_date > timezone.now().date():
        raise ValueError("End date cannot be in the future")
    return True

def format_duration(seconds):
    """Format duration in seconds to human readable format"""
    if seconds < 60:
        return f"{seconds:.1f} seconds"
    elif seconds < 3600:
        return f"{seconds / 60:.1f} minutes"
    else:
        return f"{seconds / 3600:.1f} hours"

__all__ = [
    'serialize_datetime_data',
    'CrossCountingAnalytics',
    'TablePartitioningManager',
    'DataRetentionManager',
    'TrafficFlowAnalyzer',
    'OccupancyAnalyzer',
    'PerformanceOptimizer',
    'get_timezone_aware_now',
    'convert_to_local_time',
    'validate_date_range',
    'format_duration'
]
