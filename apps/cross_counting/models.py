import logging
import uuid

from django.db import models

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

#
# class CrossCountingData(models.Model):
#     """Time series optimized cross counting data model"""
#     id = models.BigAutoField(primary_key=True)
#
#     # Device information
#     device_name = models.CharField(max_length=200, db_index=True)
#     device_ip = models.GenericIPAddressField(db_index=True)
#     device_mac = models.CharField(max_length=17)
#
#     # Channel information
#     channel = models.CharField(max_length=200, db_index=True)
#     channel_alias = models.CharField(max_length=200, blank=True)
#
#     # Cross counting data - core metrics
#     cc_in_count = models.PositiveIntegerField(default=0)
#     cc_out_count = models.PositiveIntegerField(default=0)
#     cc_total_count = models.PositiveIntegerField(default=0, db_index=True)
#
#     # Alarm data
#     alarm_snapshot = models.BooleanField(default=False)
#     alarm_subtype = models.CharField(max_length=50, db_index=True)
#     alarm_status = models.BooleanField(default=False, db_index=True)
#
#     # Relationships
#     camera = models.ForeignKey(
#         Camera,
#         on_delete=models.CASCADE,
#         related_name='cross_counting_data',
#         db_index=True
#     )
#
#     # Time series timestamp - primary partition key
#     created_at = models.DateTimeField(auto_now_add=True, db_index=True)
#     updated_at = models.DateTimeField(auto_now=True)
#
#     class Meta:
#         ordering = ['-created_at']
#         db_table = 'cross_counting_data_timeseries'
#
#     def __str__(self):
#         return f"{self.device_name} - {self.channel} - {self.created_at}"
