"""Request/correlation ID middleware and structured-logging safety."""
import json
import logging

import pytest
from django.conf import settings

from apps.core.logging import (
    CorrelationFilter,
    JsonFormatter,
    correlation_id_var,
    request_id_var,
)
from apps.core.views import HealthView

pytestmark = pytest.mark.django_db

HEALTH_URL = "/api/v1/health/"


def test_response_includes_generated_request_id(api_client):
    resp = api_client.get(HEALTH_URL)
    assert resp.status_code == 200
    request_id = resp[settings.REQUEST_ID_HEADER]
    assert request_id
    # A generated ID is a 32-char hex string.
    assert len(request_id) == 32


def test_client_request_id_is_echoed(api_client):
    resp = api_client.get(HEALTH_URL, HTTP_X_REQUEST_ID="trace-me-123")
    assert resp[settings.REQUEST_ID_HEADER] == "trace-me-123"


def test_correlation_id_defaults_to_request_id(api_client):
    resp = api_client.get(HEALTH_URL, HTTP_X_REQUEST_ID="req-abc")
    assert resp[settings.CORRELATION_ID_HEADER] == "req-abc"


def test_client_correlation_id_is_echoed(api_client):
    resp = api_client.get(
        HEALTH_URL,
        HTTP_X_REQUEST_ID="req-abc",
        HTTP_X_CORRELATION_ID="corr-xyz",
    )
    assert resp[settings.REQUEST_ID_HEADER] == "req-abc"
    assert resp[settings.CORRELATION_ID_HEADER] == "corr-xyz"


def test_access_log_never_contains_response_body(api_client, caplog):
    with caplog.at_level(logging.INFO, logger="apps.core.middleware"):
        resp = api_client.get(HEALTH_URL)
    assert resp.status_code == 200
    body = resp.json()

    access_lines = [
        record.getMessage()
        for record in caplog.records
        if record.name == "apps.core.middleware"
    ]
    assert access_lines
    for line in access_lines:
        assert line.startswith("access ")
        # None of the response body values may leak into the access line.
        assert body["service"] not in line
        assert body["version"] not in line


def test_ids_and_access_log_emitted_for_exception_response(api_client, caplog, monkeypatch):
    # An unhandled view exception is converted to a 500 by Django's
    # ``convert_exception_to_response`` wrapper, which runs *inside* this
    # middleware, so the middleware still sees a response and must tag it with
    # IDs and emit the privacy-safe access line.
    def boom(self, request):
        raise RuntimeError("deliberate-500-secret")

    monkeypatch.setattr(HealthView, "get", boom)
    api_client.raise_request_exception = False

    with caplog.at_level(logging.INFO, logger="apps.core.middleware"):
        resp = api_client.get(HEALTH_URL)

    assert resp.status_code == 500
    assert resp[settings.REQUEST_ID_HEADER]
    assert resp[settings.CORRELATION_ID_HEADER]

    access_lines = [
        record.getMessage()
        for record in caplog.records
        if record.name == "apps.core.middleware"
    ]
    assert any("status=500" in line for line in access_lines)
    # The exception message must never leak into the access line.
    assert all("deliberate-500-secret" not in line for line in access_lines)


def test_json_formatter_tags_request_and_correlation_ids():
    formatter = JsonFormatter()
    filter_ = CorrelationFilter()

    req_token = request_id_var.set("req-123")
    corr_token = correlation_id_var.set("corr-456")
    try:
        record = logging.LogRecord(
            name="apps.test", level=logging.INFO, pathname="x.py", lineno=1,
            msg="processed", args=(), exc_info=None,
        )
        filter_.filter(record)
        payload = json.loads(formatter.format(record))
    finally:
        request_id_var.reset(req_token)
        correlation_id_var.reset(corr_token)

    assert payload["request_id"] == "req-123"
    assert payload["correlation_id"] == "corr-456"
    assert payload["message"] == "processed"
    assert payload["timestamp"]
