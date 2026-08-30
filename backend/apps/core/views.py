"""Core, cross-cutting API views.

The health check is intentionally dependency-light: it must succeed as long as
the Django process can serve a request, so it does not touch the database.
"""
from __future__ import annotations

from django.conf import settings
from django.http import FileResponse, Http404, HttpRequest, HttpResponse
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthView(APIView):
    """Liveness probe for ``/api/v1/health/``."""

    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        return Response(
            {
                "status": "ok",
                "service": settings.SERVICE_NAME,
                "version": settings.SERVICE_VERSION,
            }
        )


# Path prefixes that the SPA fallback must never take over. These belong to the
# backend (or to WhiteNoise, for ``static/``) and a miss under them is a genuine
# 404 — returning the SPA shell here would mask broken API/asset URLs.
_SPA_RESERVED_PREFIXES = ("api/", "admin/", "static/", "media/")


def spa_index(request: HttpRequest, resource: str = "") -> HttpResponse:
    """Serve the built SPA ``index.html`` for client-side (deep link) routes.

    This is the *last* URL pattern, so it only runs when nothing else matched.
    It deliberately refuses to shadow backend routes and asset-looking paths:

    * requests under a reserved prefix (``/api/``, ``/admin/``, ``/static/``,
      private media) fall through to a 404 rather than the SPA shell, so a
      mistyped API or admin URL stays a real 404;
    * requests whose final path segment contains a ``.`` are treated as static
      asset requests — a missing file must be a 404, never the HTML shell (which
      would otherwise be served with the wrong content type and break caching);
    * when no SPA build is present (local dev, tests, API-only server) every
      route 404s exactly as it did before same-origin hosting existed.
    """
    path = request.path_info.lstrip("/")
    if any(path.startswith(prefix) for prefix in _SPA_RESERVED_PREFIXES):
        raise Http404()

    last_segment = path.rsplit("/", 1)[-1]
    if "." in last_segment:
        raise Http404()

    index_file = settings.SPA_INDEX_FILE
    if not index_file.is_file():
        raise Http404()

    return FileResponse(index_file.open("rb"), content_type="text/html")
