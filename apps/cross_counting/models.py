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
    """
    id = models.BigAutoField(primary_key=True)

    time = TimescaleDateTimeField(interval="1 day", db_index=True, null=True, blank=True,default=timezone.now)

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
    
    alarm_time = models.DateTimeField(db_index=True)

    camera = models.ForeignKey(
        Camera,
        on_delete=models.CASCADE,
        related_name='cross_counting_data',
        db_index=True
    )

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()
    timescale = TimescaleManager()

    class Meta:
        ordering = ['-created_at', '-time']
        db_table = 'cross_counting_data_timeseries'
        
        indexes = [
            models.Index(fields=['time', 'camera'], name='ts_time_camera_idx'),
            models.Index(fields=['time', 'channel'], name='ts_time_channel_idx'),
            models.Index(fields=['time', 'device_name'], name='ts_time_device_idx'),
            
            models.Index(fields=['camera', 'time', 'cc_total_count'], name='ts_camera_time_total_idx'),
            models.Index(fields=['channel', 'time', 'cc_in_count', 'cc_out_count'], name='ts_channel_time_counts_idx'),
            
            models.Index(
                fields=['time', 'camera'], 
                name='ts_active_alarms_idx',
                condition=models.Q(alarm_status=True)
            ),
            
            models.Index(fields=['alarm_time', 'camera'], name='ts_alarm_time_camera_idx'),
            models.Index(fields=['alarm_time', 'alarm_status'], name='ts_alarm_time_status_idx'),
            
            models.Index(fields=['device_name', 'time', 'alarm_status'], name='ts_device_time_status_idx'),
            models.Index(fields=['created_at'], name='ts_created_idx'),
            models.Index(fields=['created_at', 'camera'], name='ts_created_camera_idx'),
            models.Index(fields=['camera', 'created_at', 'cc_total_count'], name='ts_camera_created_total_idx'),
        ]
        

    def save(self, *args, **kwargs):
        if not self.time:
            self.time = self.created_at
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.device_name} - {self.channel} - {self.time}"
    
    @classmethod
    def get_latest_counts_by_camera(cls, camera_id, limit=100):
        """Get latest cross-counting data for a specific camera - optimized query"""
        return cls.objects.filter(camera_id=camera_id).order_by('-created_at')[:limit]
    
    @classmethod
    def get_hourly_aggregates(cls, camera_id, start_time, end_time):
        """
        Get hourly aggregated data for analytics dashboard
        Uses time-series indexes for fast aggregation
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
