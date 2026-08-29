"""Root URL configuration.

All API routes live under ``/api/v1/``. Feature apps contribute their own URL
includes; the Django admin is mounted separately for staff tooling.
"""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("apps.core.urls")),
    path("api/v1/", include("apps.accounts.urls")),
    path("api/v1/", include("apps.content.urls")),
    path("api/v1/", include("apps.assessments.urls")),
    path("api/v1/", include("apps.media_assets.urls")),
    path("api/v1/", include("apps.ai_services.urls")),
    path("api/v1/", include("apps.learning.urls")),
]
