from django.contrib import admin
from django.utils.html import format_html
from .models import Region, Camera, CrossCountingData


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ['name', 'occupancy', 'camera_count', 'created_at', 'updated_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['name']
    ordering = ['name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'occupancy')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def camera_count(self, obj):
        count = obj.cameras.count()
        if count > 0:
            return format_html('<span style="color: green;">{}</span>', count)
        return format_html('<span style="color: gray;">0</span>')
    camera_count.short_description = 'Cameras'


@admin.register(Camera)
class CameraAdmin(admin.ModelAdmin):
    list_display = ['name', 'region', 'status_display', 'last_data_received', 'created_at']
    list_filter = ['status', 'region', 'created_at', 'last_data_received']
    search_fields = ['name', 'region__name']
    ordering = ['name']
    readonly_fields = ['id', 'created_at', 'updated_at', 'last_data_received']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'region', 'status')
        }),
        ('Stream Configuration', {
            'fields': ('rtsp_link', 'hls_link')
        }),
        ('System Information', {
            'fields': ('id', 'last_data_received', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def status_display(self, obj):
        if obj.status:
            return format_html(
                '<span style="color: green; font-weight: bold;">● Active</span>'
            )
        return format_html(
            '<span style="color: red; font-weight: bold;">● Inactive</span>'
        )
    status_display.short_description = 'Status'

    actions = ['activate_cameras', 'deactivate_cameras']

    def activate_cameras(self, request, queryset):
        updated = queryset.update(status=True)
        self.message_user(request, f'{updated} cameras were successfully activated.')
    activate_cameras.short_description = "Activate selected cameras"

    def deactivate_cameras(self, request, queryset):
        updated = queryset.update(status=False)
        self.message_user(request, f'{updated} cameras were successfully deactivated.')
    deactivate_cameras.short_description = "Deactivate selected cameras"


@admin.register(CrossCountingData)
class CrossCountingDataAdmin(admin.ModelAdmin):
    list_display = ['device_name', 'channel', 'camera', 'cc_total_count', 'cc_in_count', 'cc_out_count', 'alarm_time', 'created_at']
    list_filter = ['device_name', 'camera', 'channel', 'alarm_status', 'alarm_subtype', 'alarm_time', 'created_at']
    search_fields = ['device_name', 'channel', 'camera__name', 'device_ip']
    ordering = ['-alarm_time', '-created_at']
    readonly_fields = ['id', 'created_at', 'updated_at']
    date_hierarchy = 'alarm_time'
    list_per_page = 50
    
    fieldsets = (
        ('Device Information', {
            'fields': ('device_name', 'device_ip', 'device_mac', 'device_phy')
        }),
        ('Channel & Camera', {
            'fields': ('channel', 'channel_alias', 'camera')
        }),
        ('Cross Counting Data', {
            'fields': ('cc_in_count', 'cc_out_count', 'cc_total_count')
        }),
        ('Alarm Information', {
            'fields': ('alarm_time', 'alarm_status', 'alarm_subtype', 'alarm_snapshot', 'record_flag')
        }),
        ('MQTT Metadata', {
            'fields': ('subscribe_id', 'data_pos'),
            'classes': ('collapse',)
        }),
        ('System Information', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('camera', 'camera__region')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
