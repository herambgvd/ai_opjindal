"""
Time-series utilities for CrossCountingData analytics
Optimized for high-frequency data analysis with PostgreSQL-specific features
"""

from django.db import connection
from django.utils import timezone
from datetime import timedelta, datetime
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
