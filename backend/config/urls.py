"""Root URL configuration.

All API routes live under ``/api/v1/``. Feature apps contribute their own URL
includes; the Django admin is mounted separately for staff tooling. A trailing
catch-all serves the single-page app for same-origin deployments (see
``apps.core.views.spa_index``); it is inert when no SPA build is present.
"""
from django.contrib import admin
from django.urls import include, path, re_path

from apps.core.views import spa_index

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("apps.core.urls")),
    path("api/v1/", include("apps.accounts.urls")),
    path("api/v1/", include("apps.content.urls")),
    path("api/v1/", include("apps.assessments.urls")),
    path("api/v1/", include("apps.media_assets.urls")),
    path("api/v1/", include("apps.ai_services.urls")),
    path("api/v1/", include("apps.learning.urls")),
    path("api/v1/", include("apps.mocks.urls")),
    # SPA fallback: matches only when nothing above did. Serves index.html for
    # client-side routes and 404s for reserved prefixes / missing assets.
    re_path(r"^(?P<resource>.*)$", spa_index, name="spa-index"),
]
