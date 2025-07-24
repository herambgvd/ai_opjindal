import uuid
from django.db import models

class Tag(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, unique=True)
    occupancy = models.PositiveIntegerField(default=0, help_text="Maximum allowed occupancy for this tag")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def get_current_occupancy(self):
        """Calculate current occupancy based on the latest CrossCountingData for all cameras in this tag."""
        from django.db.models import Sum
        cameras = self.cameras.all()
        if not cameras:
            return 0
        latest_data = CrossCountingData.objects.filter(camera__in=cameras).order_by('-created_at').first()
        if not latest_data:
            return 0
        return latest_data.cc_total_count if latest_data.cc_total_count >= 0 else 0

    def is_over_occupancy(self):
        """Check if current occupancy exceeds the limit."""
        return self.get_current_occupancy() > self.occupancy

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['occupancy'])
        ]

class Camera(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, unique=True)
    rtsp_link = models.CharField(max_length=500)
    status = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    tag = models.ForeignKey(Tag, on_delete=models.SET_NULL, null=True, blank=True, related_name='cameras')

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['name', 'status']),
            models.Index(fields=['tag'])
        ]

class CrossCountingData(models.Model):
    id = models.BigAutoField(primary_key=True)
    device_name = models.CharField(max_length=200)
    device_ip = models.GenericIPAddressField()
    device_mac = models.CharField(max_length=17)
    channel = models.CharField(max_length=200)
    channel_alias = models.CharField(max_length=200, blank=True)
    cc_in_count = models.PositiveIntegerField(default=0)
    cc_out_count = models.PositiveIntegerField(default=0)
    cc_total_count = models.PositiveIntegerField(default=0)
    alarm_snapshot = models.BooleanField(default=False)
    alarm_subtype = models.CharField(max_length=50)
    alarm_status = models.BooleanField(default=False)
    camera = models.ForeignKey(Camera, on_delete=models.CASCADE, related_name='cross_counting_data')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.device_name} - {self.channel} - {self.created_at}"

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_at', 'camera']),
            models.Index(fields=['device_ip', 'channel']),
            models.Index(fields=['alarm_subtype', 'alarm_status'])
        ]