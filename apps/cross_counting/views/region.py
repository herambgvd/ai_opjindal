import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.shortcuts import render, get_object_or_404, redirect

from ..forms import RegionForm
from ..models import Region

logger = logging.getLogger('cross_counting.views')


@login_required(login_url="account_login")
def region_list(request):
    regions = Region.objects.all().order_by('name')
    
    search_query = request.GET.get('search', '')
    if search_query:
        regions = regions.filter(name__icontains=search_query)
    
    paginator = Paginator(regions, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'regions': page_obj,
        'search_query': search_query,
        'total_regions': Region.objects.count(),
    }
    return render(request, 'cross_counting/region/main.html', context)


@login_required(login_url="account_login")
def region_create(request):
    if request.method == 'POST':
        form = RegionForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    region = form.save()
                    logger.info(f"Region '{region.name}' created by user {request.user}")
                    messages.success(request, f"Region '{region.name}' has been created successfully.")
                    return redirect('cross_counting:region_list')
            except Exception as e:
                logger.error(f"Error creating region: {e}")
                messages.error(request, "An error occurred while creating the region. Please try again.")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = RegionForm()
    
    context = {
        'form': form,
        'title': 'Create New Region',
        'submit_text': 'Create Region'
    }
    return render(request, 'cross_counting/region/region_create.html', context)


@login_required(login_url="account_login")
def region_update(request, pk):
    region = get_object_or_404(Region, pk=pk)
    
    if request.method == 'POST':
        form = RegionForm(request.POST, instance=region)
        if form.is_valid():
            try:
                with transaction.atomic():
                    updated_region = form.save()
                    logger.info(f"Region '{updated_region.name}' updated by user {request.user}")
                    messages.success(request, f"Region '{updated_region.name}' has been updated successfully.")
                    return redirect('cross_counting:region_list')
            except Exception as e:
                logger.error(f"Error updating region {region.pk}: {e}")
                messages.error(request, "An error occurred while updating the region. Please try again.")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = RegionForm(instance=region)
    
    context = {
        'form': form,
        'region': region,
        'title': f'Update Region: {region.name}',
        'submit_text': 'Update Region'
    }
    return render(request, 'cross_counting/region/region_update.html', context)


@login_required(login_url="account_login")
def region_delete(request, pk):
    region = get_object_or_404(Region, pk=pk)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                region_name = region.name
                camera_count = region.cameras.count()
                
                if camera_count > 0:
                    messages.warning(
                        request, 
                        f"Cannot delete region '{region_name}' because it has {camera_count} associated camera(s). "
                        "Please reassign or delete the cameras first."
                    )
                    return redirect('cross_counting:region_list')
                
                region.delete()
                logger.info(f"Region '{region_name}' deleted by user {request.user}")
                messages.success(request, f"Region '{region_name}' has been deleted successfully.")
                return redirect('cross_counting:region_list')
        except Exception as e:
            logger.error(f"Error deleting region {region.pk}: {e}")
            messages.error(request, "An error occurred while deleting the region. Please try again.")
    
    context = {
        'region': region,
        'camera_count': region.cameras.count(),
    }
    return render(request, 'cross_counting/region/region_delete_conf.html', context)
