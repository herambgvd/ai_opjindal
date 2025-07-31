from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import path, include
from django.views.generic import RedirectView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.web.sitemaps import StaticViewSitemap

sitemaps = {
    "static": StaticViewSitemap(),
}

urlpatterns = [
                  # redirect Django admin login to main login page
                  path("admin/login/", RedirectView.as_view(pattern_name="account_login")),
                  path("admin/", admin.site.urls),
                  path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="django.contrib.sitemaps.views.sitemap"),
                  path("accounts/", include("allauth.urls")),
                  path("users/", include("apps.users.urls")),
                  path("", include("apps.web.urls")),
                  # APPS URL
                  path("cross/", include('apps.cross_counting.urls')),
                  # API docs
                  path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
                  # Optional UI - you may wish to remove one of these depending on your preference
                  path("api/swagger/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
              ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
