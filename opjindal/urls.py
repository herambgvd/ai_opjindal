from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('accounts.urls')),  # Include accounts app URLs
    path('cross_counting/', include('cross_counting.urls')),
    path('', include('django.contrib.auth.urls')),  # Includes logout
]
