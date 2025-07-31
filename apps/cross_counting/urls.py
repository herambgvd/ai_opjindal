from django.urls import path

from .views import (region, camera)

app_name = 'cross_counting'

urlpatterns = [
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
