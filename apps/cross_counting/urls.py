from django.urls import path

from .views import (region, camera, analysis, dashboard)

app_name = 'cross_counting'

urlpatterns = [
    path('analysis/daily/', analysis.daily_analysis, name='daily_analysis'),
    path('analysis/comparative/', analysis.comparative_analysis, name='comparative_analysis'),
    path('analysis/comprehensive/', analysis.comprehensive_analysis, name='comprehensive_analysis'),
    
    path('analysis/daily/csv/', analysis.daily_analysis_csv, name='daily_analysis_csv'),
    path('analysis/comparative/csv/', analysis.comparative_analysis_csv, name='comparative_analysis_csv'),
    path('analysis/comprehensive/csv/', analysis.comprehensive_analysis_csv, name='comprehensive_analysis_csv'),
    
    path('dashboard/', dashboard.enhanced_dashboard, name='enhanced_dashboard'),
    
    path('public/occupancy/', dashboard.public_occupancy_display, name='public_occupancy_display'),
    path('public/occupancy/api/', dashboard.public_occupancy_api, name='public_occupancy_api'),
    
    # Region Management
    path('config/region/', region.region_list, name='region_list'),
    path('config/region/create/', region.region_create, name='region_create'),
    path('config/region/<int:pk>/update/', region.region_update, name='region_update'),
    path('config/region/<int:pk>/delete/', region.region_delete, name='region_delete'),

    # Camera Management
    path('config/cameras/', camera.camera_list, name='camera_list'),
    path('config/cameras/create/', camera.camera_create, name='camera_create'),
    path('config/cameras/<uuid:pk>/update/', camera.camera_update, name='camera_update'),
    path('config/cameras/<uuid:pk>/delete/', camera.camera_delete, name='camera_delete')
]
