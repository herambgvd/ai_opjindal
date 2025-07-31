import logging
from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone

from ..forms import CameraForm
from ..models import Camera, Region

logger = logging.getLogger('cross_counting.views')


@login_required(login_url="account_login")
def camera_list(request):
    cameras = Camera.objects.select_related('region').all().order_by('name')
    
    region_filter = request.GET.get('region', '')
    status_filter = request.GET.get('status', '')
    search_query = request.GET.get('search', '')
    
    if region_filter:
        cameras = cameras.filter(region_id=region_filter)
    
    if status_filter:
        status_bool = status_filter.lower() == 'true'
        cameras = cameras.filter(status=status_bool)
    
    if search_query:
        cameras = cameras.filter(name__icontains=search_query)
    
    paginator = Paginator(cameras, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    regions = Region.objects.all().order_by('name')
    
    context = {
        'cameras': page_obj,
        'regions': regions,
        'search_query': search_query,
        'region_filter': region_filter,
        'status_filter': status_filter,
        'total_cameras': Camera.objects.count(),
        'active_cameras': Camera.objects.filter(status=True).count(),
        'inactive_cameras': Camera.objects.filter(status=False).count(),
    }
    return render(request, 'cross_counting/camera/main.html', context)


@login_required(login_url="account_login")
def camera_create(request):
    if request.method == 'POST':
        form = CameraForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    camera = form.save()
                    logger.info(f"Camera '{camera.name}' created by user {request.user}")
                    messages.success(request, f"Camera has been created successfully.")
                    return redirect('cross_counting:camera_list')
            except Exception as e:
                logger.error(f"Error creating camera: {e}")
                messages.error(request, "An error occurred while creating the camera. Please try again.")
        else:
            messages.error(request, "Please correct the errors below.")
            print(form.errors)
    else:
        form = CameraForm()
    
    context = {
        'form': form,
        'title': 'Onboard New Camera',
        'submit_text': 'Create Camera'
    }
    return render(request, 'cross_counting/camera/camera_create.html', context)


@login_required(login_url="account_login")
def camera_update(request, pk):
    camera = get_object_or_404(Camera, pk=pk)
    
    if request.method == 'POST':
        form = CameraForm(request.POST, instance=camera)
        if form.is_valid():
            try:
                with transaction.atomic():
                    updated_camera = form.save()
                    if updated_camera.status and not camera.status:
                        updated_camera.last_data_received = timezone.now()
                        updated_camera.save(update_fields=['last_data_received'])
                    
                    logger.info(f"Camera '{updated_camera.name}' updated by user {request.user}")
                    messages.success(request, f"Camera has been updated successfully.")
                    return redirect('cross_counting:camera_list')
            except Exception as e:
                logger.error(f"Error updating camera {camera.pk}: {e}")
                messages.error(request, "An error occurred while updating the camera. Please try again.")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = CameraForm(instance=camera)
    
    context = {
        'form': form,
        'camera': camera,
        'title': f'Update Camera: {camera.name}',
        'submit_text': 'Update Camera'
    }
    return render(request, 'cross_counting/camera/camera_update.html', context)


@login_required(login_url="account_login")
def camera_delete(request, pk):
    camera = get_object_or_404(Camera, pk=pk)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                camera_name = camera.name
                camera.delete()
                logger.info(f"Camera '{camera_name}' deleted by user {request.user}")
                messages.success(request, f"Camera has been deleted successfully.")
                return redirect('cross_counting:camera_list')
        except Exception as e:
            logger.error(f"Error deleting camera {camera.pk}: {e}")
            messages.error(request, "An error occurred while deleting the camera. Please try again.")
    
    context = {
        'camera': camera,
    }
    return render(request, 'cross_counting/camera/camera_delete_conf.html', context)
