import logging
import uuid

from django.db import models
from django.utils import timezone
from timescale.db.models.fields import TimescaleDateTimeField
from timescale.db.models.managers import TimescaleManager

logger = logging.getLogger(__name__)


class Region(models.Model):
    """Location tags with caching for frequent reads"""
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, unique=True, db_index=True)
    occupancy = models.PositiveIntegerField(default=0, help_text="Maximum allowed occupancy for this tag",
                                            db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['occupancy']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return self.name


class Camera(models.Model):
    """Camera model with status tracking"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, unique=True, db_index=True)
    rtsp_link = models.CharField(max_length=500)
    hls_link = models.CharField(max_length=500)
    status = models.BooleanField(default=True, db_index=True)
    last_data_received = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    region = models.ForeignKey(Region, on_delete=models.SET_NULL, null=True, blank=True,
                               related_name='cameras', db_index=True)

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['name', 'status']),
            models.Index(fields=['last_data_received']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return self.name


class CrossCountingData(models.Model):
    """
    TimescaleDB-optimized model for high-frequency MQTT payload storage (every 2 seconds)
    Uses hypertables for fast analytical queries with automatic partitioning
    UPDATED: Ensures proper created_at usage for all analytics
    """
    id = models.BigAutoField(primary_key=True)

    # FIXED: Ensure time field is properly set to created_at for consistency
    time = TimescaleDateTimeField(interval="1 day", db_index=True, null=True, blank=True)

    device_name = models.CharField(max_length=200, db_index=True)
    device_ip = models.GenericIPAddressField(db_index=True)
    device_mac = models.CharField(max_length=17)
    device_phy = models.CharField(max_length=50, blank=True)

    # Channel information - core identifier for analytics
    channel = models.CharField(max_length=200, db_index=True)
    channel_alias = models.CharField(max_length=200, blank=True)

    cc_in_count = models.PositiveIntegerField(default=0)
    cc_out_count = models.PositiveIntegerField(default=0)
    cc_total_count = models.PositiveIntegerField(default=0)

    # Alarm data - for filtering and alerting
    alarm_snapshot = models.BooleanField(default=False)
    alarm_subtype = models.CharField(max_length=50, db_index=True)
    alarm_status = models.BooleanField(default=False, db_index=True)
    record_flag = models.CharField(max_length=10, blank=True)

    subscribe_id = models.PositiveIntegerField(null=True, blank=True)
    data_pos = models.PositiveIntegerField(null=True, blank=True)

    # Keep alarm_time for reference but use created_at for analytics
    alarm_time = models.DateTimeField(db_index=True)

    camera = models.ForeignKey(
        Camera,
        on_delete=models.CASCADE,
        related_name='cross_counting_data',
        db_index=True
    )

    # CRITICAL: created_at is the primary field for all analytics
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()
    timescale = TimescaleManager()

    class Meta:
        ordering = ['-created_at', '-time']
        db_table = 'cross_counting_data_timeseries'

        indexes = [
            # UPDATED: Focus on created_at for analytics
            models.Index(fields=['created_at', 'camera'], name='ts_created_camera_idx'),
            models.Index(fields=['created_at', 'channel'], name='ts_created_channel_idx'),
            models.Index(fields=['created_at', 'device_name'], name='ts_created_device_idx'),

            models.Index(fields=['camera', 'created_at', 'cc_total_count'], name='ts_camera_created_total_idx'),
            models.Index(fields=['channel', 'created_at', 'cc_in_count', 'cc_out_count'],
                         name='ts_channel_created_counts_idx'),

            models.Index(
                fields=['created_at', 'camera'],
                name='ts_active_alarms_created_idx',
                condition=models.Q(alarm_status=True)
            ),

            # Keep some alarm_time indexes for compatibility
            models.Index(fields=['alarm_time', 'camera'], name='ts_alarm_time_camera_idx'),
            models.Index(fields=['alarm_time', 'alarm_status'], name='ts_alarm_time_status_idx'),

            models.Index(fields=['device_name', 'created_at', 'alarm_status'], name='ts_device_created_status_idx'),
            models.Index(fields=['created_at'], name='ts_created_idx'),

            # Additional indexes for hourly analytics
            models.Index(fields=['camera', 'created_at'], name='ts_camera_created_idx'),
            models.Index(fields=['created_at', 'cc_in_count'], name='ts_created_in_idx'),
            models.Index(fields=['created_at', 'cc_out_count'], name='ts_created_out_idx'),
        ]

    def save(self, *args, **kwargs):
        """
        FIXED: Ensure time field is always set to created_at for TimescaleDB compatibility
        This ensures all analytics use consistent timestamps
        """
        # Set created_at first if it's a new object
        if not self.pk and not self.created_at:
            self.created_at = timezone.now()

        # Always sync time field with created_at for TimescaleDB
        if self.created_at:
            self.time = self.created_at
        elif not self.time:
            self.time = timezone.now()

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.device_name} - {self.channel} - {self.created_at}"

    @classmethod
    def get_latest_counts_by_camera(cls, camera_id, limit=100):
        """
        Get latest cross-counting data for a specific camera - optimized query
        FIXED: Uses created_at for consistency
        """
        return cls.objects.filter(camera_id=camera_id).order_by('-created_at')[:limit]

    @classmethod
    def get_hourly_aggregates(cls, camera_id, start_time, end_time):
        """
        Get hourly aggregated data for analytics dashboard
        Uses time-series indexes for fast aggregation
        FIXED: Uses created_at for all time-based operations
        """
        from django.db.models import Max, Min, Avg, Count
        from django.db.models.functions import TruncHour

        return cls.objects.filter(
            camera_id=camera_id,
            created_at__range=[start_time, end_time]
        ).annotate(
            hour=TruncHour('created_at')
        ).values('hour').annotate(
            max_in_count=Max('cc_in_count'),
            max_out_count=Max('cc_out_count'),
            max_total_count=Max('cc_total_count'),
            min_in_count=Min('cc_in_count'),
            min_out_count=Min('cc_out_count'),
            min_total_count=Min('cc_total_count'),
            avg_total_count=Avg('cc_total_count'),
            data_points=Count('id')
        ).order_by('hour')

    @classmethod
    def get_daily_peak_counts(cls, camera_id, start_date, end_date):
        """
        Get daily peak counts (before reset at 11:59 PM)
        Useful for daily analytics and reporting
        FIXED: Uses created_at for date filtering
        """
        from django.db.models import Max
        from django.db.models.functions import TruncDate

        return cls.objects.filter(
            camera_id=camera_id,
            created_at__date__range=[start_date, end_date]
        ).annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            peak_in_count=Max('cc_in_count'),
            peak_out_count=Max('cc_out_count'),
            peak_total_count=Max('cc_total_count')
        ).order_by('date')

    @classmethod
    def get_real_time_dashboard_data(cls, camera_ids=None, minutes=30):
        """
        Get recent data for real-time dashboard
        Optimized for frequent polling
        FIXED: Uses created_at for time filtering
        """
        from django.utils import timezone
        from datetime import timedelta

        queryset = cls.objects.select_related('camera')

        if camera_ids:
            queryset = queryset.filter(camera_id__in=camera_ids)

        since = timezone.now() - timedelta(minutes=minutes)

        return queryset.filter(
            created_at__gte=since
        ).order_by('-created_at')[:1000]  # Limit for performance

    @classmethod
    def get_hourly_last_values_for_region(cls, region_id, start_time, end_time):
        """
        NEW METHOD: Get last value per hour for each camera in a region
        This is the core method for proper hourly analytics
        """
        from django.db import connection

        with connection.cursor() as cursor:
            cursor.execute("""
                           WITH ranked_data AS (SELECT ccd.camera_id,
                                                       ccd.cc_in_count,
                                                       ccd.cc_out_count,
                                                       ccd.cc_total_count,
                                                       EXTRACT(HOUR FROM ccd.created_at) as hour, ccd.created_at, ROW_NUMBER() OVER (
                               PARTITION BY ccd.camera_id, EXTRACT (HOUR FROM ccd.created_at)
                               ORDER BY ccd.created_at DESC
                               ) as rn
                           FROM cross_counting_data_timeseries ccd
                               JOIN cross_counting_camera c
                           ON ccd.camera_id = c.id
                           WHERE c.region_id = %s
                             AND c.status = true
                             AND ccd.created_at >= %s
                             AND ccd.created_at
                               < %s
                               )
                           SELECT camera_id, hour, cc_in_count, cc_out_count, cc_total_count
                           FROM ranked_data
                           WHERE rn = 1
                           ORDER BY camera_id, hour
                           """, [region_id, start_time, end_time])

            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]


class HourlyAggregateView(models.Model):
    """Materialized view for hourly aggregated cross-counting data"""
    camera = models.ForeignKey(Camera, on_delete=models.DO_NOTHING)
    hour = models.DateTimeField()
    max_in_count = models.PositiveIntegerField()
    max_out_count = models.PositiveIntegerField()
    max_total_count = models.PositiveIntegerField()
    min_in_count = models.PositiveIntegerField()
    min_out_count = models.PositiveIntegerField()
    min_total_count = models.PositiveIntegerField()
    avg_total_count = models.FloatField()
    data_points = models.PositiveIntegerField()

    class Meta:
        managed = False
        db_table = 'cross_counting_hourly_aggregates'

    def __str__(self):
        return f"{self.camera.name} - {self.hour}"


class DailyPeakView(models.Model):
    """Materialized view for daily peak counts"""
    camera = models.ForeignKey(Camera, on_delete=models.DO_NOTHING)
    date = models.DateField()
    peak_in_count = models.PositiveIntegerField()
    peak_out_count = models.PositiveIntegerField()
    peak_total_count = models.PositiveIntegerField()

    class Meta:
        managed = False
        db_table = 'cross_counting_daily_peaks'

    def __str__(self):
        return f"{self.camera.name} - {self.date}"