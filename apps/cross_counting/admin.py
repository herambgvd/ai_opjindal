import csv
import io
from django.contrib import admin, messages
from django.shortcuts import render, redirect
from django.urls import path
from django.utils.html import format_html
from django.http import HttpResponseRedirect
from django.core.exceptions import ValidationError
from .models import Region, Camera, CrossCountingData, HourlyAggregateView, DailyPeakView


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

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('upload-csv/', self.upload_csv, name='camera_upload_csv'),
        ]
        return custom_urls + urls

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['show_csv_upload'] = 'true'
        return super().changelist_view(request, extra_context=extra_context)

    def upload_csv(self, request):
        if request.method == "POST":
            csv_file = request.FILES.get("csv_file")

            if not csv_file:
                messages.error(request, "Please select a CSV file to upload.")
                return redirect("..")

            if not csv_file.name.endswith('.csv'):
                messages.error(request, "Please upload a valid CSV file.")
                return redirect("..")

            try:
                data_set = csv_file.read().decode('UTF-8')
                io_string = io.StringIO(data_set)
                reader = csv.DictReader(io_string)

                required_headers = ['name', 'region']
                optional_headers = ['status', 'rtsp_link', 'hls_link']
                all_headers = required_headers + optional_headers

                if not all(header in (reader.fieldnames or []) for header in required_headers):
                    messages.error(
                        request,
                        f"CSV file must contain the following required columns: {', '.join(required_headers)}. "
                        f"Optional columns: {', '.join(optional_headers)}"
                    )
                    return redirect("..")

                created_count = 0
                updated_count = 0
                error_count = 0
                errors = []

                for row_num, row in enumerate(reader, start=2):  # Start from 2 because row 1 is headers
                    try:
                        camera_name = row.get('name', '').strip()
                        region_name = row.get('region', '').strip()

                        if not camera_name or not region_name:
                            errors.append(f"Row {row_num}: Camera name and region are required.")
                            error_count += 1
                            continue

                        try:
                            region = Region.objects.get(name=region_name)
                        except Region.DoesNotExist:
                            errors.append(f"Row {row_num}: Region '{region_name}' does not exist.")
                            error_count += 1
                            continue

                        status_str = row.get('status', 'true').strip().lower()
                        status = status_str in ['true', '1', 'yes', 'active', 'on']
                        rtsp_link = row.get('rtsp_link', '').strip()
                        hls_link = row.get('hls_link', '').strip()

                        camera, created = Camera.objects.get_or_create(
                            name=camera_name,
                            defaults={
                                'region': region,
                                'status': status,
                                'rtsp_link': rtsp_link,
                                'hls_link': hls_link,
                            }
                        )

                        if created:
                            created_count += 1
                        else:
                            camera.region = region
                            camera.status = status
                            if rtsp_link:
                                camera.rtsp_link = rtsp_link
                            if hls_link:
                                camera.hls_link = hls_link
                            camera.save()
                            updated_count += 1

                    except Exception as e:
                        errors.append(f"Row {row_num}: {str(e)}")
                        error_count += 1

                if created_count > 0:
                    messages.success(request, f"Successfully created {created_count} cameras.")
                if updated_count > 0:
                    messages.success(request, f"Successfully updated {updated_count} cameras.")
                if error_count > 0:
                    messages.warning(request, f"Failed to process {error_count} rows.")
                    for error in errors[:10]:  # Show first 10 errors
                        messages.error(request, error)
                    if len(errors) > 10:
                        messages.error(request, f"... and {len(errors) - 10} more errors.")

                if created_count == 0 and updated_count == 0 and error_count == 0:
                    messages.info(request, "No cameras were processed from the CSV file.")

            except Exception as e:
                messages.error(request, f"Error processing CSV file: {str(e)}")

            return redirect("..")

        context = {
            'title': 'Upload Cameras CSV',
            'opts': self.model._meta,
            'has_view_permission': self.has_view_permission(request),
        }
        return render(request, 'admin/cross_counting/camera/upload_csv.html', context)


@admin.register(CrossCountingData)
class CrossCountingDataAdmin(admin.ModelAdmin):
    list_display = ['device_name', 'channel', 'camera', 'cc_total_count', 'cc_in_count', 'cc_out_count',
                    'created_at_display', 'alarm_time_display']
    list_filter = ['device_name', 'camera', 'channel', 'alarm_status', 'alarm_subtype', 'created_at', 'alarm_time']
    search_fields = ['device_name', 'channel', 'camera__name', 'device_ip']
    ordering = ['-created_at', '-alarm_time']  # Order by created_at first, then alarm_time
    readonly_fields = ['id', 'created_at', 'updated_at']
    date_hierarchy = 'created_at'  # Use created_at for date hierarchy
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
        ('Timing Information', {
            'fields': ('created_at', 'alarm_time', 'time'),
            'description': 'created_at is when data entered system, alarm_time is from device'
        }),
        ('Alarm Information', {
            'fields': ('alarm_status', 'alarm_subtype', 'alarm_snapshot', 'record_flag')
        }),
        ('MQTT Metadata', {
            'fields': ('subscribe_id', 'data_pos'),
            'classes': ('collapse',)
        }),
        ('System Information', {
            'fields': ('id', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def created_at_display(self, obj):
        """Display created_at with better formatting"""
        if obj.created_at:
            return format_html(
                '<span style="color: green; font-weight: bold;" title="System Creation Time">{}</span>',
                obj.created_at.strftime('%Y-%m-%d %H:%M:%S')
            )
        return '-'

    created_at_display.short_description = 'Created At (System)'
    created_at_display.admin_order_field = 'created_at'

    def alarm_time_display(self, obj):
        """Display alarm_time with different formatting"""
        if obj.alarm_time:
            return format_html(
                '<span style="color: blue;" title="Device Alarm Time">{}</span>',
                obj.alarm_time.strftime('%Y-%m-%d %H:%M:%S')
            )
        return '-'

    alarm_time_display.short_description = 'Alarm Time (Device)'
    alarm_time_display.admin_order_field = 'alarm_time'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('camera', 'camera__region')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    # Custom actions for data analysis
    actions = ['export_selected_data', 'analyze_time_differences']

    def export_selected_data(self, request, queryset):
        """Export selected data with created_at timestamps"""
        import csv
        from django.http import HttpResponse

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="cross_counting_data_export.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'Device Name', 'Camera', 'Channel', 'In Count', 'Out Count', 'Total Count',
            'Created At (System)', 'Alarm Time (Device)', 'Time Difference (seconds)'
        ])

        for obj in queryset.select_related('camera'):
            time_diff = ''
            if obj.created_at and obj.alarm_time:
                time_diff = (obj.created_at - obj.alarm_time).total_seconds()

            writer.writerow([
                obj.device_name,
                obj.camera.name if obj.camera else '',
                obj.channel,
                obj.cc_in_count,
                obj.cc_out_count,
                obj.cc_total_count,
                obj.created_at.strftime('%Y-%m-%d %H:%M:%S') if obj.created_at else '',
                obj.alarm_time.strftime('%Y-%m-%d %H:%M:%S') if obj.alarm_time else '',
                f'{time_diff:.2f}' if time_diff != '' else ''
            ])

        self.message_user(request, f"Exported {queryset.count()} records.")
        return response

    export_selected_data.short_description = "Export selected data with timestamps"

    def analyze_time_differences(self, request, queryset):
        """Analyze time differences between created_at and alarm_time"""
        from django.db.models import Avg, Min, Max
        from django.db.models import F, ExpressionWrapper, DurationField

        # Calculate time differences
        queryset_with_diff = queryset.annotate(
            time_diff=ExpressionWrapper(
                F('created_at') - F('alarm_time'),
                output_field=DurationField()
            )
        ).filter(
            created_at__isnull=False,
            alarm_time__isnull=False
        )

        if not queryset_with_diff.exists():
            self.message_user(request, "No records with both created_at and alarm_time found.", level=messages.WARNING)
            return

        stats = queryset_with_diff.aggregate(
            avg_diff=Avg('time_diff'),
            min_diff=Min('time_diff'),
            max_diff=Max('time_diff'),
            count=Count('id')
        )

        avg_seconds = stats['avg_diff'].total_seconds() if stats['avg_diff'] else 0
        min_seconds = stats['min_diff'].total_seconds() if stats['min_diff'] else 0
        max_seconds = stats['max_diff'].total_seconds() if stats['max_diff'] else 0

        message = (
            f"Time Difference Analysis for {stats['count']} records:\n"
            f"Average delay: {avg_seconds:.2f} seconds\n"
            f"Minimum delay: {min_seconds:.2f} seconds\n"
            f"Maximum delay: {max_seconds:.2f} seconds"
        )

        self.message_user(request, message)

    analyze_time_differences.short_description = "Analyze time differences (created_at vs alarm_time)"


@admin.register(HourlyAggregateView)
class HourlyAggregateViewAdmin(admin.ModelAdmin):
    list_display = ['camera', 'hour', 'max_total_count', 'avg_total_count', 'data_points']
    list_filter = ['camera', 'hour']
    search_fields = ['camera__name']
    ordering = ['-hour']
    readonly_fields = ['camera', 'hour', 'max_in_count', 'max_out_count', 'max_total_count', 'min_in_count',
                       'min_out_count', 'min_total_count', 'avg_total_count', 'data_points']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(DailyPeakView)
class DailyPeakViewAdmin(admin.ModelAdmin):
    list_display = ['camera', 'date', 'peak_total_count', 'peak_in_count', 'peak_out_count']
    list_filter = ['camera', 'date']
    search_fields = ['camera__name']
    ordering = ['-date']
    readonly_fields = ['camera', 'date', 'peak_in_count', 'peak_out_count', 'peak_total_count']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False