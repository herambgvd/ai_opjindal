from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, TemplateView
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Count, Avg, Max, Min, Q
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Tag, Camera, CrossCountingData
from .forms import TagForm, CameraForm
import json


class DashboardView(LoginRequiredMixin, TemplateView):
    """Main dashboard with real-time monitoring"""
    template_name = 'cross_counting/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get all tags with their cameras and latest data
        tags = Tag.objects.all().prefetch_related('cameras__cross_counting_data')
        tag_data = []

        total_occupancy = 0
        total_capacity = 0
        active_cameras = 0
        alerts_count = 0

        for tag in tags:
            cameras = tag.cameras.filter(status=True)
            camera_data = []
            tag_occupancy = 0

            for camera in cameras:
                latest_data = camera.cross_counting_data.order_by('-created_at').first()
                camera_info = {
                    'camera': camera,
                    'latest_in_count': latest_data.cc_in_count if latest_data else 0,
                    'latest_out_count': latest_data.cc_out_count if latest_data else 0,
                    'latest_total_count': latest_data.cc_total_count if latest_data else 0,
                    'last_updated': latest_data.created_at if latest_data else None,
                    'status': 'online' if latest_data and
                                          (timezone.now() - latest_data.created_at).seconds < 300 else 'offline'
                }
                camera_data.append(camera_info)

                if latest_data:
                    tag_occupancy += latest_data.cc_total_count

                active_cameras += 1

            is_over_capacity = tag_occupancy > tag.occupancy if tag.occupancy > 0 else False
            if is_over_capacity:
                alerts_count += 1

            tag_info = {
                'tag': tag,
                'cameras': camera_data,
                'current_occupancy': tag_occupancy,
                'max_occupancy': tag.occupancy,
                'is_over_capacity': is_over_capacity,
                'occupancy_percentage': (tag_occupancy / tag.occupancy * 100) if tag.occupancy > 0 else 0,
            }
            tag_data.append(tag_info)

            total_occupancy += tag_occupancy
            total_capacity += tag.occupancy

        # Dashboard statistics
        context.update({
            'tag_data': tag_data,
            'total_occupancy': total_occupancy,
            'total_capacity': total_capacity,
            'active_cameras': active_cameras,
            'alerts_count': alerts_count,
            'capacity_percentage': (total_occupancy / total_capacity * 100) if total_capacity > 0 else 0,
            'total_tags': tags.count(),
        })
        print(context)
        return context


class ReportsView(LoginRequiredMixin, TemplateView):
    """Enhanced Reports with Today's Analytics Dashboard"""
    template_name = 'cross_counting/reports.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Today's date
        today = timezone.now().date()

        # Get today's analytics data
        today_data = self.get_today_analytics()

        # Get hourly data for today
        hourly_data = self.get_hourly_data(today)

        # Get location-wise data for today
        location_data = self.get_location_data(today)

        context.update({
            'today': today,
            'today_stats': today_data,
            'hourly_data': hourly_data,
            'location_data': location_data,
        })

        return context

    def get_today_analytics(self):
        """Get today's summary statistics"""
        today = timezone.now().date()

        today_queryset = CrossCountingData.objects.filter(
            created_at__date=today
        )

        if not today_queryset.exists():
            return {
                'current_occupancy': 0,
                'peak_occupancy': 0,
                'total_entries': 0,
                'total_exits': 0
            }

        # Get current occupancy (latest total count across all cameras)
        current_occupancy = 0
        for camera in Camera.objects.filter(status=True):
            latest_data = camera.cross_counting_data.filter(
                created_at__date=today
            ).order_by('-created_at').first()
            if latest_data:
                current_occupancy += latest_data.cc_total_count

        stats = today_queryset.aggregate(
            peak_occupancy=Max('cc_total_count'),
            total_entries=Sum('cc_in_count'),
            total_exits=Sum('cc_out_count')
        )

        return {
            'current_occupancy': current_occupancy,
            'peak_occupancy': stats['peak_occupancy'] or 0,
            'total_entries': stats['total_entries'] or 0,
            'total_exits': stats['total_exits'] or 0
        }

    def get_hourly_data(self, target_date):
        """Get hourly breakdown for a specific date"""
        hourly_data = []

        for hour in range(24):
            hour_data = CrossCountingData.objects.filter(
                created_at__date=target_date,
                created_at__hour=hour
            ).aggregate(
                avg_occupancy=Avg('cc_total_count'),
                entries=Sum('cc_in_count'),
                exits=Sum('cc_out_count')
            )

            hourly_data.append({
                'hour': hour,
                'avg_occupancy': hour_data['avg_occupancy'] or 0,
                'entries': hour_data['entries'] or 0,
                'exits': hour_data['exits'] or 0
            })

        return hourly_data

    def get_location_data(self, target_date):
        """Get location-wise data for a specific date"""
        location_data = []

        for tag in Tag.objects.all():
            cameras = tag.cameras.filter(status=True)
            if not cameras.exists():
                continue

            # Get today's data for this tag's cameras
            tag_data = CrossCountingData.objects.filter(
                camera__in=cameras,
                created_at__date=target_date
            )

            if not tag_data.exists():
                location_data.append({
                    'tag': tag,
                    'current_occupancy': 0,
                    'entries_today': 0,
                    'exits_today': 0,
                    'peak_today': 0,
                    'utilization_percentage': 0
                })
                continue

            # Calculate current occupancy (latest total for each camera)
            current_occupancy = 0
            for camera in cameras:
                latest_data = camera.cross_counting_data.filter(
                    created_at__date=target_date
                ).order_by('-created_at').first()
                if latest_data:
                    current_occupancy += latest_data.cc_total_count

            # Get aggregated data
            stats = tag_data.aggregate(
                entries_today=Sum('cc_in_count'),
                exits_today=Sum('cc_out_count'),
                peak_today=Max('cc_total_count')
            )

            utilization_percentage = (current_occupancy / tag.occupancy * 100) if tag.occupancy > 0 else 0

            location_data.append({
                'tag': tag,
                'current_occupancy': current_occupancy,
                'entries_today': stats['entries_today'] or 0,
                'exits_today': stats['exits_today'] or 0,
                'peak_today': stats['peak_today'] or 0,
                'utilization_percentage': utilization_percentage
            })

        return location_data


class ConfigView(LoginRequiredMixin, TemplateView):
    """Configuration dashboard"""
    template_name = 'cross_counting/config/main.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Configuration overview
        context.update({
            'total_tags': Tag.objects.count(),
            'total_cameras': Camera.objects.count(),
            'active_cameras': Camera.objects.filter(status=True).count(),
            'recent_tags': Tag.objects.order_by('-created_at')[:5],
            'recent_cameras': Camera.objects.order_by('-created_at')[:5],
        })

        return context


# Tag Management Views
class TagListView(LoginRequiredMixin, ListView):
    model = Tag
    context_object_name = 'tags'
    template_name = 'cross_counting/config/tag/tag_list.html'
    paginate_by = 20

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Add statistics for each tag
        tags_with_stats = []
        for tag in context['tags']:
            camera_count = tag.cameras.count()
            active_cameras = tag.cameras.filter(status=True).count()
            current_occupancy = tag.get_current_occupancy()

            tags_with_stats.append({
                'tag': tag,
                'camera_count': camera_count,
                'active_cameras': active_cameras,
                'current_occupancy': current_occupancy,
                'utilization_rate': (current_occupancy / tag.occupancy * 100) if tag.occupancy > 0 else 0,
                'is_over_capacity': current_occupancy > tag.occupancy if tag.occupancy > 0 else False
            })

        context['tags_with_stats'] = tags_with_stats
        return context


class TagCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Tag
    form_class = TagForm
    template_name = 'cross_counting/config/tag/tag_form.html'
    success_url = reverse_lazy('cross_counting:tag_list')
    success_message = "Tag '%(name)s' created successfully."


class TagUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Tag
    form_class = TagForm
    template_name = 'cross_counting/config/tag/tag_form.html'
    success_url = reverse_lazy('cross_counting:tag_list')
    success_message = "Tag '%(name)s' updated successfully."


class TagDeleteView(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    model = Tag
    template_name = 'cross_counting/config/tag/tag_confirm_delete.html'
    success_url = reverse_lazy('cross_counting:tag_list')
    success_message = "Tag deleted successfully."

    def delete(self, request, *args, **kwargs):
        from django.contrib import messages
        messages.success(self.request, self.success_message)
        return super().delete(request, *args, **kwargs)


# Camera Management Views
class CameraListView(LoginRequiredMixin, ListView):
    model = Camera
    context_object_name = 'cameras'
    template_name = 'cross_counting/config/camera/camera_list.html'
    paginate_by = 20

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Add statistics for each camera
        cameras_with_stats = []
        for camera in context['cameras']:
            latest_data = camera.cross_counting_data.order_by('-created_at').first()
            last_activity = latest_data.created_at if latest_data else None

            # Determine status
            if not camera.status:
                status = 'disabled'
            elif latest_data and (timezone.now() - latest_data.created_at).seconds < 300:
                status = 'online'
            else:
                status = 'offline'

            cameras_with_stats.append({
                'camera': camera,
                'latest_data': latest_data,
                'last_activity': last_activity,
                'status': status,
                'current_count': latest_data.cc_total_count if latest_data else 0,
            })

        context['cameras_with_stats'] = cameras_with_stats
        return context


class CameraCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Camera
    form_class = CameraForm
    template_name = 'cross_counting/config/camera/camera_form.html'
    success_url = reverse_lazy('cross_counting:camera_list')
    success_message = "Camera '%(name)s' created successfully."


class CameraUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Camera
    form_class = CameraForm
    template_name = 'cross_counting/config/camera/camera_form.html'
    success_url = reverse_lazy('cross_counting:camera_list')
    success_message = "Camera '%(name)s' updated successfully."


class CameraDeleteView(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    model = Camera
    template_name = 'cross_counting/config/camera/camera_confirm_delete.html'
    success_url = reverse_lazy('cross_counting:camera_list')
    success_message = "Camera deleted successfully."

    def delete(self, request, *args, **kwargs):
        from django.contrib import messages
        messages.success(self.request, self.success_message)
        return super().delete(request, *args, **kwargs)


# API Views for real-time data
@login_required
def dashboard_api(request):
    """API endpoint for dashboard real-time data"""
    tags = Tag.objects.all()
    data = []

    for tag in tags:
        tag_occupancy = tag.get_current_occupancy()
        data.append({
            'id': tag.id,
            'name': tag.name,
            'current_occupancy': tag_occupancy,
            'max_occupancy': tag.occupancy,
            'is_over_capacity': tag.is_over_occupancy(),
            'cameras': [{
                'id': camera.id,
                'name': camera.name,
                'status': camera.status,
                'latest_count': camera.cross_counting_data.order_by('-created_at').first().cc_total_count
                if camera.cross_counting_data.exists() else 0
            } for camera in tag.cameras.filter(status=True)]
        })

    return JsonResponse({'tags': data})


@login_required
def reports_api(request):
    """API endpoint for reports data"""
    # Get date range
    days = int(request.GET.get('days', 7))
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)

    # Get hourly data for charts
    hourly_data = []
    for i in range(24):
        hour_data = CrossCountingData.objects.filter(
            created_at__hour=i,
            created_at__range=[start_date, end_date]
        ).aggregate(
            avg_count=Avg('cc_total_count'),
            max_count=Max('cc_total_count')
        )

        hourly_data.append({
            'hour': i,
            'avg_count': hour_data['avg_count'] or 0,
            'max_count': hour_data['max_count'] or 0
        })

    return JsonResponse({'hourly_data': hourly_data})