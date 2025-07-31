from django.contrib import admin
from django.utils.html import format_html
from .models import Region, Camera


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
