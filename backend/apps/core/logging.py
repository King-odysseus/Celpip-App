"""Structured logging primitives with request/correlation context.

The request ID and correlation ID are carried on a :class:`contextvars.ContextVar`
so any log record emitted during a request can be tagged with them, without
threading request objects through every call site. Records never include
response bodies or private audio/text: only method, path, status, and timing.
"""
from __future__ import annotations

import contextvars
import json
import logging
from datetime import UTC, datetime

# The correlation ID is a client-supplied trace across systems; the request ID
# is the per-request identifier generated here when the client sent none.
request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default="-"
)
correlation_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "correlation_id", default="-"
)

_MISSING = "-"


def current_request_id() -> str:
    """Return the request ID for the current context, or ``"-"``."""
    return request_id_var.get()


def current_correlation_id() -> str:
    """Return the correlation ID for the current context, or ``"-"``."""
    return correlation_id_var.get()


class CorrelationFilter(logging.Filter):
    """Injects the ambient request/correlation IDs into each record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        record.correlation_id = correlation_id_var.get()
        return True


class JsonFormatter(logging.Formatter):
    """Render one log record as a single JSON object.

    Extra attributes (``request_id``, ``correlation_id``, ``user_id``) are
    included automatically; ``exc_info`` becomes a ``traceback`` string. The
    message itself is never replaced or enriched with body/audio content.
    """

    _RESERVED = {
        "name",
        "msg",
        "args",
        "levelname",
        "levelno",
        "pathname",
        "filename",
        "module",
        "exc_info",
        "exc_text",
        "stack_info",
        "lineno",
        "funcName",
        "created",
        "msecs",
        "relativeCreated",
        "thread",
        "threadName",
        "processName",
        "process",
        "taskName",
        "message",
    }

    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=UTC
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", _MISSING),
            "correlation_id": getattr(record, "correlation_id", _MISSING),
        }
        for key, value in record.__dict__.items():
            if key not in self._RESERVED and not key.startswith("_"):
                payload[key] = value
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def log_access(
    logger: logging.Logger,
    *,
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    user_id: int | None,
) -> None:
    """Emit one structured access line. Never logs query strings or bodies."""
    logger.info(
        "access method=%s path=%s status=%s duration_ms=%.1f user_id=%s",
        method,
        path,
        status_code,
        duration_ms,
        user_id if user_id is not None else _MISSING,
    )
