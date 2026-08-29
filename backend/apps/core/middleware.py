"""Request/correlation ID middleware and access logging.

Attaches a request ID to every response (``X-Request-ID``), echoes or
generates a correlation ID (``X-Correlation-ID``), and emits a single
structured access line per request. It never reads or logs request/response
bodies, so response text and private audio are never written to logs.
"""
from __future__ import annotations

import logging
import re
import time
import uuid

from django.conf import settings

from .logging import (
    correlation_id_var,
    log_access,
    request_id_var,
)

logger = logging.getLogger("apps.core.middleware")

# Request/correlation IDs are echoed into headers and logs. Restrict them to a
# small safe character set and a bounded length so a hostile header cannot
# smuggle newlines into the log stream.
_ID_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")
_MAX_ID_LENGTH = 128


def _sanitize(value: str) -> str:
    cleaned = _ID_PATTERN.sub("", (value or "").strip())[:_MAX_ID_LENGTH]
    return cleaned or uuid.uuid4().hex


class RequestCorrelationMiddleware:
    """Tag each request/response with trace IDs and log a summary line."""

    def __init__(self, get_response) -> None:  # noqa: ANN001
        self.get_response = get_response

    def __call__(self, request):  # noqa: ANN001
        request_id = _sanitize(request.headers.get(settings.REQUEST_ID_HEADER, ""))
        correlation_id = _sanitize(
            request.headers.get(settings.CORRELATION_ID_HEADER, request_id)
        )

        request.request_id = request_id
        request.correlation_id = correlation_id

        request_token = request_id_var.set(request_id)
        correlation_token = correlation_id_var.set(correlation_id)
        started = time.perf_counter()
        try:
            # Unhandled view exceptions are converted into a 500 response by
            # Django's ``convert_exception_to_response`` wrapper, which sits
            # *inside* this middleware in the chain. ``get_response`` therefore
            # returns a 500 response here rather than raising, so the request ID
            # headers and access line are emitted for exception responses too.
            response = self.get_response(request)
            response[settings.REQUEST_ID_HEADER] = request_id
            response[settings.CORRELATION_ID_HEADER] = correlation_id

            user = getattr(request, "user", None)
            user_id = (
                user.pk if user is not None and getattr(user, "is_authenticated", False) else None
            )
            log_access(
                logger,
                method=request.method,
                path=request.path,
                status_code=response.status_code,
                duration_ms=(time.perf_counter() - started) * 1000,
                user_id=user_id,
            )
            return response
        finally:
            request_id_var.reset(request_token)
            correlation_id_var.reset(correlation_token)
