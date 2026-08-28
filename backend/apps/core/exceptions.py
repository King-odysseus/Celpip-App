"""Project-wide DRF exception handling.

Every framework-raised error (throttling, permission, auth, validation) is
reshaped into the platform's consistent envelope::

    {"code": "...", "message": "...", "fields": {}}

so the SPA can handle failures uniformly. View code that already returns this
shape (see ``apps.accounts.views.error``) is unaffected.
"""
from __future__ import annotations

from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

# Map common DRF status codes to stable machine-readable codes.
_STATUS_CODES = {
    400: "invalid_input",
    401: "not_authenticated",
    403: "permission_denied",
    404: "not_found",
    405: "method_not_allowed",
    429: "throttled",
}


def exception_handler(exc, context) -> Response | None:
    response = drf_exception_handler(exc, context)
    if response is None:
        return None

    status_code = response.status_code
    code = getattr(exc, "default_code", None) or _STATUS_CODES.get(
        status_code, "error"
    )

    detail = response.data
    fields: dict = {}
    message = "Request failed."

    if isinstance(detail, dict) and "detail" in detail:
        message = str(detail["detail"])
    elif isinstance(detail, dict):
        fields = detail
        message = "Some fields were invalid."
    elif isinstance(detail, list):
        message = "; ".join(str(item) for item in detail)

    response.data = {"code": str(code), "message": message, "fields": fields}
    return response
