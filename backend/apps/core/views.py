"""Core, cross-cutting API views.

The health check is intentionally dependency-light: it must succeed as long as
the Django process can serve a request, so it does not touch the database.
"""
from __future__ import annotations

from django.conf import settings
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
