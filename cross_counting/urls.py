from django.urls import path
from . import views

app_name = 'cross_counting'

urlpatterns = [
    # Dashboard
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    # Tag CRUD
    path('tags/', views.TagListView.as_view(), name='tag_list'),
    path('tags/create/', views.TagCreateView.as_view(), name='tag_create'),
    path('tags/<int:pk>/update/', views.TagUpdateView.as_view(), name='tag_update'),
    path('tags/<int:pk>/delete/', views.TagDeleteView.as_view(), name='tag_delete'),
    # Camera CRUD
    path('cameras/', views.CameraListView.as_view(), name='camera_list'),
    path('cameras/create/', views.CameraCreateView.as_view(), name='camera_create'),
    path('cameras/<uuid:pk>/update/', views.CameraUpdateView.as_view(), name='camera_update'),
    path('cameras/<uuid:pk>/delete/', views.CameraDeleteView.as_view(), name='camera_delete'),
]