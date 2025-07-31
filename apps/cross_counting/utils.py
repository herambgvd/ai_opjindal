"""
Time-series utilities for CrossCountingData analytics
Optimized for high-frequency data analysis with PostgreSQL-specific features
"""

from django.db import connection
from django.utils import timezone
from datetime import timedelta, datetime, date
from typing import List, Dict, Any, Optional


class CrossCountingAnalytics:
    """
    High-performance analytics utilities for cross-counting time-series data
    Uses PostgreSQL-specific optimizations for fast dashboard and reporting
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
                    MIN(ccd.alarm_time) as first_data,
                    MAX(ccd.alarm_time) as last_data,
                    AVG(ccd.cc_total_count) as avg_total
                FROM cross_counting_data_timeseries ccd
                JOIN cross_counting_camera c ON ccd.camera_id = c.id
                WHERE ccd.alarm_time >= %s 
                AND c.id = ANY(%s)
                GROUP BY c.id, c.name
                ORDER BY c.name
            """, [since, camera_ids])
            
            columns = [col[0] for col in cursor.description] if cursor.description else []
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    @staticmethod
    def get_traffic_flow_analysis(camera_id: str, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        """
        Analyze traffic flow patterns with entry/exit calculations
        Handles the daily reset logic at 11:59 PM
        """
        with connection.cursor() as cursor:
            cursor.execute("""
                WITH daily_resets AS (
                    SELECT 
                        DATE(alarm_time) as date,
                        MAX(cc_in_count) as daily_max_in,
                        MAX(cc_out_count) as daily_max_out,
                        MAX(cc_total_count) as daily_max_total,
                        MIN(cc_in_count) as daily_min_in,
                        MIN(cc_out_count) as daily_min_out,
                        COUNT(*) as data_points
                    FROM cross_counting_data_timeseries
                    WHERE camera_id = %s 
                    AND alarm_time BETWEEN %s AND %s
                    GROUP BY DATE(alarm_time)
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
                    MIN(alarm_time) as earliest_data,
                    MAX(alarm_time) as latest_data,
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
                alarm_time__lt=cutoff_date
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
            min_date=Min('alarm_time'),
            max_date=Max('alarm_time')
        )
        
        daily_stats = CrossCountingData.objects.annotate(
            date=TruncDate('alarm_time')
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
    Implements monthly partitioning strategy for time-series data
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
                CREATE INDEX {partition_name}_alarm_time_idx 
                ON {partition_name} (alarm_time);
            """)
            
            cursor.execute(f"""
                CREATE INDEX {partition_name}_camera_time_idx 
                ON {partition_name} (camera_id, alarm_time);
            """)
    
    @staticmethod
    def setup_partitioning():
        """Convert existing table to partitioned table (for future use)"""
        pass

    @staticmethod
    def get_daily_analysis_data(region_id: int, date: date) -> Dict[str, Any]:
        """Get comprehensive daily analysis for all cameras in a region"""
        from .models import Camera, CrossCountingData
        
        cameras = Camera.objects.filter(region_id=region_id, status=True)
        camera_ids = list(cameras.values_list('id', flat=True))
        
        if not camera_ids:
            return {"cameras": [], "summary": {}, "hourly_trends": []}
        
        daily_data = []
        total_peak_in = 0
        total_peak_out = 0
        total_peak_total = 0
        
        for camera in cameras:
            peaks = CrossCountingData.get_daily_peak_counts(
                camera.id, date, date
            ).first()
            
            if peaks:
                camera_data = {
                    "camera_name": camera.name,
                    "peak_in": peaks['peak_in_count'],
                    "peak_out": peaks['peak_out_count'],
                    "peak_total": peaks['peak_total_count']
                }
                daily_data.append(camera_data)
                total_peak_in += peaks['peak_in_count']
                total_peak_out += peaks['peak_out_count']
                total_peak_total += peaks['peak_total_count']
        
        start_datetime = timezone.make_aware(datetime.combine(date, datetime.min.time()))
        end_datetime = timezone.make_aware(datetime.combine(date, datetime.max.time()))
        
        hourly_trends = []
        for camera in cameras:
            hourly_data = CrossCountingData.get_hourly_aggregates(
                camera.id, start_datetime, end_datetime
            )
            hourly_trends.append({
                "camera_name": camera.name,
                "hourly_data": list(hourly_data)
            })
        
        return {
            "cameras": daily_data,
            "summary": {
                "total_peak_in": total_peak_in,
                "total_peak_out": total_peak_out,
                "total_peak_total": total_peak_total,
                "active_cameras": len(daily_data)
            },
            "hourly_trends": hourly_trends,
            "region_hourly_aggregates": TablePartitioningManager.get_hourly_region_aggregates(
                region_id, start_datetime, end_datetime
            )
        }
    
    @staticmethod
    def get_comparative_analysis_data(region_id: int, base_date: date, compare_date: date) -> Dict[str, Any]:
        """Get comparative analysis between two dates for a region"""
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
        
        return {
            "base_date": base_date,
            "compare_date": compare_date,
            "comparison": comparison,
            "base_summary": base_data["summary"],
            "compare_summary": compare_data["summary"],
            "base_hourly_aggregates": base_data.get("region_hourly_aggregates", {"hourly_data": []}),
            "compare_hourly_aggregates": compare_data.get("region_hourly_aggregates", {"hourly_data": []})
        }
    
    @staticmethod
    def get_comprehensive_analysis_data(region_id: int, from_date: date, to_date: date) -> Dict[str, Any]:
        """Get comprehensive analysis for a date range (max 7 days)"""
        from .models import Camera, CrossCountingData
        
        cameras = Camera.objects.filter(region_id=region_id, status=True)
        
        daily_trends = []
        for camera in cameras:
            daily_data = CrossCountingData.get_daily_peak_counts(
                camera.id, from_date, to_date
            )
            daily_trends.append({
                "camera_name": camera.name,
                "daily_data": list(daily_data)
            })
        
        total_days = (to_date - from_date).days + 1
        
        start_datetime = timezone.make_aware(datetime.combine(from_date, datetime.min.time()))
        end_datetime = timezone.make_aware(datetime.combine(to_date, datetime.max.time()))
        
        return {
            "from_date": from_date,
            "to_date": to_date,
            "total_days": total_days,
            "daily_trends": daily_trends,
            "cameras": list(cameras.values('id', 'name')),
            "region_hourly_aggregates": TablePartitioningManager.get_hourly_region_aggregates(
                region_id, start_datetime, end_datetime
            )
        }

    @staticmethod
    def get_current_occupancy_data() -> List[Dict[str, Any]]:
        """
        Get current occupancy percentage for all regions for public display
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
                latest_data = CrossCountingData.objects.filter(
                    camera=camera,
                    time__gte=recent_time
                ).order_by('-time').first()
                
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
        """Get comprehensive platform statistics for dashboard"""
        from .models import Region, Camera, CrossCountingData
        from django.utils import timezone
        from datetime import timedelta
        
        total_regions = Region.objects.count()
        total_cameras = Camera.objects.count()
        active_cameras = Camera.objects.filter(status=True).count()
        
        since_24h = timezone.now() - timedelta(hours=24)
        recent_data_points = CrossCountingData.objects.filter(
            time__gte=since_24h
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
        """Get region cards data with cameras and their latest counts for enhanced dashboard"""
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
                    time__gte=recent_time
                ).order_by('-time').first()
                
                if latest_data:
                    camera_occupancy = max(0, latest_data.cc_in_count - latest_data.cc_out_count)
                    camera_info = {
                        'name': camera.name,
                        'latest_in_count': latest_data.cc_in_count,
                        'latest_out_count': latest_data.cc_out_count,
                        'current_occupancy': camera_occupancy,
                        'last_updated': latest_data.time,
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

    @staticmethod
    def get_hourly_region_aggregates(region_id: int, start_time, end_time) -> Dict[str, Any]:
        """
        Get hourly aggregated In/Out counts for all cameras in a region
        Returns cumulative increasing values by summing all region cameras per hour
        """
        from .models import Camera, CrossCountingData
        from django.db.models import Sum, Max
        from django.db.models.functions import TruncHour
        
        cameras = Camera.objects.filter(region_id=region_id, status=True)
        camera_ids = list(cameras.values_list('id', flat=True))
        
        if not camera_ids:
            return {"hourly_data": [], "region_name": ""}
        
        hourly_aggregates = CrossCountingData.objects.filter(
            camera_id__in=camera_ids,
            time__range=[start_time, end_time]
        ).annotate(
            hour=TruncHour('time')
        ).values('hour').annotate(
            total_in_count=Sum('cc_in_count'),
            total_out_count=Sum('cc_out_count'),
            max_in_count=Max('cc_in_count'),
            max_out_count=Max('cc_out_count')
        ).order_by('hour')
        
        region_name = cameras.first().region.name if cameras.exists() else ""
        
        return {
            "hourly_data": list(hourly_aggregates),
            "region_name": region_name,
            "camera_count": len(camera_ids)
        }
