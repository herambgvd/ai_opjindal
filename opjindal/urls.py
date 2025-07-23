from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # Root path goes to accounts landing page
    path('', include('accounts.urls')),

    # Cross counting app
    path('cross_counting/', include('cross_counting.urls')),

    # Django auth URLs (logout, etc.)
    path('', include('django.contrib.auth.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)