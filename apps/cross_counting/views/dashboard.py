import logging
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.cache import cache_page
from django.utils import timezone

from ..utils import TablePartitioningManager, CrossCountingAnalytics

logger = logging.getLogger('cross_counting.views')


@login_required(login_url="account_login")
def enhanced_dashboard(request):
    """Enhanced dashboard with comprehensive platform statistics"""
    try:
        dashboard_data = TablePartitioningManager.get_dashboard_statistics()
        enhanced_regions = TablePartitioningManager.get_enhanced_dashboard_data()

        # ---- Add inactive_cameras for template (avoid math/filter errors) ----
        total = int(dashboard_data.get("total_cameras", 0) or 0)
        active = int(dashboard_data.get("active_cameras", 0) or 0)
        dashboard_data["inactive_cameras"] = max(total - active, 0)

    except Exception as e:
        logger.error(f"Error loading dashboard: {e}")

        # SAFE DEFAULTS so the template never crashes
        dashboard_data = {
            'total_regions': 0,
            'total_cameras': 0,
            'active_cameras': 0,
            'inactive_cameras': 0,     # include this so template is happy
            'recent_data_points': 0,
            'total_current_occupancy': 0,
            'health_metrics': {},
            'volume_stats': {},
            'occupancy_data': [],
        }
        enhanced_regions = []

    # Render with guaranteed keys
    return render(
        request,
        'dashboard/main.html',
        {
            'dashboard_data': dashboard_data,
            'enhanced_regions': enhanced_regions,
            'title': 'Platform Dashboard',
        },
    )


@cache_page(60)
def public_occupancy_display(request):
    """Public occupancy display for TV/guest viewing"""
    try:
        occupancy_data = TablePartitioningManager.get_current_occupancy_data()
        context = {
            'occupancy_data': occupancy_data,
            'title': 'Region Occupancy Status'
        }
        return render(request, 'cross_counting/public/occupancy_display.html', context)

    except Exception as e:
        logger.error(f"Error loading public occupancy display: {e}")
        return render(request, 'cross_counting/public/occupancy_display.html', {
            'occupancy_data': [],
            'error': 'Unable to load occupancy data'
        })


@cache_page(30)
def public_occupancy_api(request):
    """JSON API for public occupancy data"""
    try:
        occupancy_data = TablePartitioningManager.get_current_occupancy_data()
        return JsonResponse({
            'success': True,
            'data': occupancy_data,
            'timestamp': timezone.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Error in public occupancy API: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Unable to load occupancy data'
        }, status=500)
