from django.urls import path
from . import views

app_name = 'cross_counting'

urlpatterns = [
    # Main Dashboard
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),

    # Reports
    path('reports/', views.ReportsView.as_view(), name='reports'),

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
]