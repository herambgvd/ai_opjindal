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

        return context


class ReportsView(LoginRequiredMixin, TemplateView):
    """Reports and analytics dashboard"""
    template_name = 'cross_counting/reports.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Date range for reports (default: last 7 days)
        end_date = timezone.now()
        start_date = end_date - timedelta(days=7)

        # Get date range from query params if provided
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')

        if date_from:
            start_date = datetime.strptime(date_from, '%Y-%m-%d').replace(tzinfo=timezone.get_current_timezone())
        if date_to:
            end_date = datetime.strptime(date_to, '%Y-%m-%d').replace(tzinfo=timezone.get_current_timezone())

        # Analytics data
        data_queryset = CrossCountingData.objects.filter(
            created_at__range=[start_date, end_date]
        )

        # Summary statistics
        summary_stats = {
            'total_entries': data_queryset.aggregate(
                total_in=Count('cc_in_count'),
                total_out=Count('cc_out_count'),
                avg_occupancy=Avg('cc_total_count'),
                max_occupancy=Max('cc_total_count'),
                min_occupancy=Min('cc_total_count')
            )
        }

        # Daily trends
        daily_data = []
        current_date = start_date.date()
        while current_date <= end_date.date():
            day_data = data_queryset.filter(created_at__date=current_date).aggregate(
                avg_occupancy=Avg('cc_total_count'),
                max_occupancy=Max('cc_total_count'),
                total_entries=Count('id')
            )
            daily_data.append({
                'date': current_date,
                'avg_occupancy': day_data['avg_occupancy'] or 0,
                'max_occupancy': day_data['max_occupancy'] or 0,
                'total_entries': day_data['total_entries']
            })
            current_date += timedelta(days=1)

        # Tag-wise analytics
        tag_analytics = []
        for tag in Tag.objects.all():
            tag_data = data_queryset.filter(camera__tag=tag).aggregate(
                avg_occupancy=Avg('cc_total_count'),
                max_occupancy=Max('cc_total_count'),
                total_entries=Count('id')
            )
            tag_analytics.append({
                'tag': tag,
                'avg_occupancy': tag_data['avg_occupancy'] or 0,
                'max_occupancy': tag_data['max_occupancy'] or 0,
                'total_entries': tag_data['total_entries'],
                'utilization_rate': (tag_data['avg_occupancy'] / tag.occupancy * 100) if tag.occupancy > 0 and tag_data[
                    'avg_occupancy'] else 0
            })

        context.update({
            'summary_stats': summary_stats,
            'daily_data': daily_data,
            'tag_analytics': tag_analytics,
            'date_from': start_date.date(),
            'date_to': end_date.date(),
        })

        return context


class ConfigView(LoginRequiredMixin, TemplateView):
    """Configuration dashboard"""
    template_name = 'cross_counting/config.html'

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
    template_name = 'cross_counting/tag_list.html'
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
    template_name = 'cross_counting/tag_form.html'
    success_url = reverse_lazy('cross_counting:tag_list')
    success_message = "Tag '%(name)s' created successfully."


class TagUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Tag
    form_class = TagForm
    template_name = 'cross_counting/tag_form.html'
    success_url = reverse_lazy('cross_counting:tag_list')
    success_message = "Tag '%(name)s' updated successfully."


class TagDeleteView(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    model = Tag
    template_name = 'cross_counting/tag_confirm_delete.html'
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
    template_name = 'cross_counting/camera_list.html'
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
    template_name = 'cross_counting/camera_form.html'
    success_url = reverse_lazy('cross_counting:camera_list')
    success_message = "Camera '%(name)s' created successfully."


class CameraUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Camera
    form_class = CameraForm
    template_name = 'cross_counting/camera_form.html'
    success_url = reverse_lazy('cross_counting:camera_list')
    success_message = "Camera '%(name)s' updated successfully."


class CameraDeleteView(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    model = Camera
    template_name = 'cross_counting/camera_confirm_delete.html'
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