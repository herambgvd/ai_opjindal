from django.contrib import admin
from .models import Tag, Camera, CrossCountingData

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'occupancy', 'current_occupancy', 'created_at', 'updated_at')
    search_fields = ('name',)

    def current_occupancy(self, obj):
        return obj.get_current_occupancy()
    current_occupancy.short_description = 'Current Occupancy'

@admin.register(Camera)
class CameraAdmin(admin.ModelAdmin):
    list_display = ('name', 'rtsp_link', 'status', 'tag', 'created_at', 'updated_at')
    list_filter = ('status', 'tag')
    search_fields = ('name', 'rtsp_link')

@admin.register(CrossCountingData)
class CrossCountingDataAdmin(admin.ModelAdmin):
    list_display = ('device_name', 'channel', 'created_at', 'cc_in_count', 'cc_out_count', 'cc_total_count', 'camera')
    list_filter = ('alarm_status', 'alarm_subtype', 'camera')
    search_fields = ('device_name', 'channel', 'device_ip')
    date_hierarchy = 'created_at'