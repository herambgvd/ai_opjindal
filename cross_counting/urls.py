
from django.urls import path
from . import views

app_name = 'cross_counting'

urlpatterns = [
    # Main Dashboard
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),

    # Reports and Analytics
    path('reports/', views.ReportsView.as_view(), name='reports'),
    # path('reports/daily-analysis/', views.DailyAnalysisView.as_view(), name='daily_analysis'),
    # path('reports/comparative-analysis/', views.ComparativeAnalysisView.as_view(), name='comparative_analysis'),
    # path('reports/comprehensive-analysis/', views.ComprehensiveAnalysisView.as_view(), name='comprehensive_analysis'),

    # Configuration
    path('config/', views.ConfigView.as_view(), name='config'),

    # Tag Management
    path('config/tags/', views.TagListView.as_view(), name='tag_list'),
    path('config/tags/create/', views.TagCreateView.as_view(), name='tag_create'),
    path('config/tags/<int:pk>/update/', views.TagUpdateView.as_view(), name='tag_update'),
    path('config/tags/<int:pk>/delete/', views.TagDeleteView.as_view(), name='tag_delete'),

    # Camera Management
    path('config/cameras/', views.CameraListView.as_view(), name='camera_list'),
    path('config/cameras/create/', views.CameraCreateView.as_view(), name='camera_create'),
    path('config/cameras/<uuid:pk>/update/', views.CameraUpdateView.as_view(), name='camera_update'),
    path('config/cameras/<uuid:pk>/delete/', views.CameraDeleteView.as_view(), name='camera_delete'),

    # API Endpoints
    path('api/dashboard/', views.dashboard_api, name='dashboard_api'),
    path('api/reports/', views.reports_api, name='reports_api'),
    # path('api/today-analytics/', views.today_analytics_api, name='today_analytics_api'),

    # Export Endpoints
    # path('export/today-report/', views.export_today_report, name='export_today_report'),
    # path('export/daily-analysis/', views.export_daily_analysis, name='export_daily_analysis'),
    # path('export/comparative-analysis/', views.export_comparative_analysis, name='export_comparative_analysis'),
    # path('export/comprehensive-analysis/', views.export_comprehensive_analysis, name='export_comprehensive_analysis'),
]