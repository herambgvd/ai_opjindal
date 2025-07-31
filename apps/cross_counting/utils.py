"""
Time-series utilities for CrossCountingData analytics
Optimized for high-frequency data analysis with PostgreSQL-specific features
COMPLETE VERSION - All methods included with compatible timezone handling
"""

import logging
import json
from django.core.serializers.json import DjangoJSONEncoder
from django.db import connection
from django.db.models import Q, Max, Min, Count, Avg, Sum
from django.db.models.functions import TruncHour, TruncDay, Extract
from django.utils import timezone
from datetime import timedelta, datetime, date
from typing import List, Dict, Any, Optional
from .models import CrossCountingData, Camera, Region

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
    """
    High-performance analytics utilities for cross-counting time-series data
    Uses PostgreSQL-specific optimizations for fast dashboard and reporting
    COMPLETE VERSION - All methods with compatible timezone handling
    """

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
        Uses raw SQL for maximum performance with large datasets
        """
        since = timezone.now() - timedelta(hours=hours)

        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    c.name as camera_name,
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
                AND c.id = ANY(%s)
                GROUP BY c.id, c.name
                ORDER BY c.name
            """, [since, camera_ids])

            columns = [col[0] for col in cursor.description] if cursor.description else []
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    @staticmethod
    def get_traffic_flow_analysis(camera_id: str, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        """
        Analyze traffic flow patterns with entry/exit calculations using created_at
        Handles the daily reset logic at 11:59 PM
        """
        with connection.cursor() as cursor:
            cursor.execute("""
                WITH daily_resets AS (
                    SELECT 
                        DATE(created_at) as date,
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
                SELECT 
                    date,
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
    def get_system_health_metrics(minutes: int = 60) -> Dict[str, Any]:
        """
        Get system health metrics for monitoring data ingestion
        """
        since = timezone.now() - timedelta(minutes=minutes)

        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_records,
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
        Should be run periodically (e.g., daily via cron job)
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


class DataRetentionManager:
    """
    Manage data retention for time-series data
    Important for maintaining performance with high-frequency inserts
    """

    @staticmethod
    def cleanup_old_data(days_to_keep: int = 90) -> int:
        """
        Remove data older than specified days
        Returns number of records deleted
        """
        from .models import CrossCountingData

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
        ).order_by('-date')[:30]  # Last 30 days

        return {
            "total_records": total_records,
            "date_range": date_range,
            "daily_stats": list(daily_stats),
            "avg_daily_records": total_records / max(1, (date_range['max_date'] - date_range['min_date']).days) if date_range['max_date'] and date_range['min_date'] else 0
        }


class TablePartitioningManager:
    """
    Utilities for managing table partitioning for very high volume data
    COMPLETE VERSION - All methods with compatible timezone handling
    """

    @staticmethod
    def create_monthly_partition(year: int, month: int):
        """Create a monthly partition for cross-counting data"""
        from calendar import monthrange

        start_date = datetime(year, month, 1)
        _, last_day = monthrange(year, month)
        end_date = datetime(year, month, last_day, 23, 59, 59)

        partition_name = f"cross_counting_data_timeseries_{year}_{month:02d}"

        with connection.cursor() as cursor:
            cursor.execute(f"""
                CREATE TABLE {partition_name} PARTITION OF cross_counting_data_timeseries
                FOR VALUES FROM ('{start_date}') TO ('{end_date}');
            """)

            cursor.execute(f"""
                CREATE INDEX {partition_name}_created_at_idx 
                ON {partition_name} (created_at);
            """)

            cursor.execute(f"""
                CREATE INDEX {partition_name}_camera_time_idx 
                ON {partition_name} (camera_id, created_at);
            """)

    @staticmethod
    def setup_partitioning():
        """Convert existing table to partitioned table (for future use)"""
        pass

    @staticmethod
    def get_daily_analysis_data(region_id: int, date: date) -> Dict[str, Any]:
        """
        Get comprehensive daily analysis for all cameras in a region using created_at
        SIMPLIFIED: Uses date filtering without complex timezone localization
        """
        from .models import Camera, CrossCountingData
        from django.db.models import Max

        cameras = Camera.objects.filter(region_id=region_id, status=True)
        camera_ids = list(cameras.values_list('id', flat=True))

        if not camera_ids:
            return {"cameras": [], "summary": {}, "region_hourly_aggregates": {"hourly_data": [], "individual_camera_data": []}}

        daily_data = []
        total_peak_in = 0
        total_peak_out = 0
        total_peak_total = 0

        # SIMPLIFIED: Use date filtering instead of complex timezone handling
        from datetime import timedelta

        # Create simple datetime range for the target date
        start_datetime = datetime.combine(date, datetime.min.time())
        end_datetime = datetime.combine(date, datetime.max.time())

        # Make them timezone-aware using Django's timezone
        start_datetime = timezone.make_aware(start_datetime)
        end_datetime = timezone.make_aware(end_datetime)

        print(f"Daily analysis date range: {start_datetime} to {end_datetime}")

        for camera in cameras:
            # Get daily peaks using created_at with date range
            peaks = CrossCountingData.objects.filter(
                camera=camera,
                created_at__date=date  # Simplified: use date filtering
            ).aggregate(
                peak_in_count=Max('cc_in_count'),
                peak_out_count=Max('cc_out_count'),
                peak_total_count=Max('cc_total_count')
            )

            if peaks['peak_in_count'] is not None:
                camera_data = {
                    "camera_name": camera.name,
                    "peak_in": peaks['peak_in_count'],
                    "peak_out": peaks['peak_out_count'],
                    "peak_total": peaks['peak_total_count']
                }
                daily_data.append(camera_data)
                total_peak_in += peaks['peak_in_count'] or 0
                total_peak_out += peaks['peak_out_count'] or 0
                total_peak_total += peaks['peak_total_count'] or 0

        result = {
            "cameras": daily_data,
            "summary": {
                "total_peak_in": total_peak_in,
                "total_peak_out": total_peak_out,
                "total_peak_total": total_peak_total,
                "active_cameras": len(daily_data)
            },
            "region_hourly_aggregates": TablePartitioningManager.get_hourly_region_aggregates(
                region_id, start_datetime, end_datetime
            )
        }

        return serialize_datetime_data(result)

    @staticmethod
    def get_comparative_analysis_data(region_id: int, base_date: date, compare_date: date) -> Dict[str, Any]:
        """
        Get comparative analysis between two dates for a region
        """
        base_data = TablePartitioningManager.get_daily_analysis_data(region_id, base_date)
        compare_data = TablePartitioningManager.get_daily_analysis_data(region_id, compare_date)

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

        result = {
            "base_date": base_date,
            "compare_date": compare_date,
            "comparison": comparison,
            "base_summary": base_data["summary"],
            "compare_summary": compare_data["summary"],
            "base_hourly_aggregates": base_data.get("region_hourly_aggregates", {"hourly_data": []}),
            "compare_hourly_aggregates": compare_data.get("region_hourly_aggregates", {"hourly_data": []})
        }

        return serialize_datetime_data(result)

    @staticmethod
    def get_comprehensive_analysis_data(region_id: int, from_date: date, to_date: date) -> Dict[str, Any]:
        """
        Get comprehensive analysis for a date range (max 7 days) using created_at
        SIMPLIFIED: Uses date range filtering
        """
        from .models import Camera, CrossCountingData
        from django.db.models import Max
        from django.db.models.functions import TruncDate

        cameras = Camera.objects.filter(region_id=region_id, status=True)

        daily_trends = []

        # SIMPLIFIED: Use date range filtering
        start_datetime = datetime.combine(from_date, datetime.min.time())
        end_datetime = datetime.combine(to_date, datetime.max.time())

        # Make them timezone-aware
        start_datetime = timezone.make_aware(start_datetime)
        end_datetime = timezone.make_aware(end_datetime)

        print(f"Comprehensive analysis date range: {start_datetime} to {end_datetime}")

        for camera in cameras:
            # Get daily peaks using date range filtering
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

        result = {
            "from_date": from_date,
            "to_date": to_date,
            "total_days": total_days,
            "daily_trends": daily_trends,
            "cameras": [{"id": str(cam.id), "name": cam.name} for cam in cameras],
            "region_hourly_aggregates": TablePartitioningManager.get_hourly_region_aggregates(
                region_id, start_datetime, end_datetime
            )
        }

        return serialize_datetime_data(result)

    @staticmethod
    def get_hourly_region_aggregates(region_id: int, start_time, end_time) -> Dict[str, Any]:
        """
        Get hourly aggregated In/Out counts for all cameras in a region
        SIMPLIFIED VERSION: More compatible timezone handling
        """
        from .models import Camera, CrossCountingData
        from django.db.models import Max
        from collections import defaultdict
        from datetime import datetime, timedelta

        cameras = Camera.objects.filter(region_id=region_id, status=True)
        camera_ids = list(cameras.values_list('id', flat=True))

        if not camera_ids:
            return {
                "hourly_data": [{"hour": h, "total_in_count": 0, "total_out_count": 0} for h in range(24)],
                "region_name": "",
                "camera_count": 0,
                "individual_camera_data": []
            }

        print(f"Querying hourly data from {start_time} to {end_time}")

        # SIMPLIFIED: Use simpler SQL without timezone conversion for compatibility
        with connection.cursor() as cursor:
            cursor.execute("""
                WITH ranked_data AS (
                    SELECT 
                        camera_id,
                        cc_in_count,
                        cc_out_count,
                        EXTRACT(HOUR FROM created_at) as hour,
                        created_at,
                        ROW_NUMBER() OVER (
                            PARTITION BY camera_id, EXTRACT(HOUR FROM created_at) 
                            ORDER BY created_at DESC
                        ) as rn
                    FROM cross_counting_data_timeseries
                    WHERE camera_id = ANY(%s)
                    AND created_at >= %s 
                    AND created_at <= %s
                ),
                last_values_per_hour AS (
                    SELECT 
                        camera_id,
                        hour,
                        cc_in_count,
                        cc_out_count
                    FROM ranked_data
                    WHERE rn = 1
                ),
                region_hourly_totals AS (
                    SELECT 
                        hour,
                        SUM(cc_in_count) as total_in_count,
                        SUM(cc_out_count) as total_out_count
                    FROM last_values_per_hour
                    GROUP BY hour
                ),
                all_hours AS (
                    SELECT generate_series(0, 23) as hour
                )
                SELECT 
                    ah.hour,
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

        # Debug: Print how many hours of data we got
        non_zero_hours = [h for h in hourly_data if h['total_in_count'] > 0 or h['total_out_count'] > 0]
        if non_zero_hours:
            print(f"Found data for hours: {[h['hour'] for h in non_zero_hours]}")
            print(f"Last hour with data: {max([h['hour'] for h in non_zero_hours])}")

        # Get individual camera data for detailed charts
        individual_camera_data = []
        camera_objects = {cam.id: cam for cam in cameras}

        with connection.cursor() as cursor:
            cursor.execute("""
                WITH ranked_camera_data AS (
                    SELECT 
                        camera_id,
                        cc_in_count,
                        cc_out_count,
                        EXTRACT(HOUR FROM created_at) as hour,
                        created_at,
                        ROW_NUMBER() OVER (
                            PARTITION BY camera_id, EXTRACT(HOUR FROM created_at) 
                            ORDER BY created_at DESC
                        ) as rn
                    FROM cross_counting_data_timeseries
                    WHERE camera_id = ANY(%s)
                    AND created_at >= %s 
                    AND created_at <= %s
                ),
                camera_last_values AS (
                    SELECT 
                        camera_id,
                        hour,
                        cc_in_count,
                        cc_out_count
                    FROM ranked_camera_data
                    WHERE rn = 1
                ),
                all_hours AS (
                    SELECT generate_series(0, 23) as hour
                ),
                all_cameras AS (
                    SELECT unnest(%s::uuid[]) as camera_id
                )
                SELECT 
                    ac.camera_id,
                    ah.hour,
                    COALESCE(clv.cc_in_count, 0) as cc_in_count,
                    COALESCE(clv.cc_out_count, 0) as cc_out_count
                FROM all_cameras ac
                CROSS JOIN all_hours ah
                LEFT JOIN camera_last_values clv ON ac.camera_id = clv.camera_id AND ah.hour = clv.hour
                ORDER BY ac.camera_id, ah.hour
            """, [camera_ids, start_time, end_time, camera_ids])

            # Group by camera
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

            # Convert to final format with proper serialization
            for camera_id in camera_ids:
                if camera_id in camera_objects:
                    individual_camera_data.append({
                        'camera_id': str(camera_id),  # Convert UUID to string
                        'camera_name': camera_objects[camera_id].name,
                        'hourly_data': camera_data_dict[camera_id]
                    })

        region_name = cameras.first().region.name if cameras.exists() else ""

        # Apply serialization to the entire result
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
        Get current occupancy percentage for all regions for public display using created_at
        Occupancy is calculated as cc_in_count - cc_out_count (difference, not sum)
        Values are clamped to prevent negative occupancy
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
                # Use created_at for recent data
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
        Get comprehensive platform statistics for dashboard using created_at
        """
        from .models import Region, Camera, CrossCountingData
        from django.utils import timezone
        from datetime import timedelta

        total_regions = Region.objects.count()
        total_cameras = Camera.objects.count()
        active_cameras = Camera.objects.filter(status=True).count()

        # Use created_at for recent data points
        since_24h = timezone.now() - timedelta(hours=24)
        recent_data_points = CrossCountingData.objects.filter(
            created_at__gte=since_24h
        ).count()

        health_metrics = CrossCountingAnalytics.get_system_health_metrics(minutes=60)

        volume_stats = DataRetentionManager.get_data_volume_stats()

        occupancy_data = TablePartitioningManager.get_current_occupancy_data()
        total_current_occupancy = sum(item['current_count'] for item in occupancy_data)
        total_max_occupancy = sum(item['max_occupancy'] for item in occupancy_data)
        avg_occupancy_percentage = (total_current_occupancy / total_max_occupancy * 100) if total_max_occupancy > 0 else 0.0

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
        Get region cards data with cameras and their latest counts for enhanced dashboard using created_at
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
                # Use created_at for latest data
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
                        'last_updated': latest_data.created_at,  # Use created_at
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