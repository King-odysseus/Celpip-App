"""Tests for the /api/v1/health/ endpoint."""
from django.urls import reverse


def test_health_returns_ok(api_client):
    response = api_client.get("/api/v1/health/")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "celpip-backend"
    assert body["version"] == "0.1.0"


def test_health_url_name_resolves(api_client):
    # The route is reachable via its namespaced name as well as its raw path.
    url = reverse("core:health")
    assert url == "/api/v1/health/"

    response = api_client.get(url)
    assert response.status_code == 200


def test_health_does_not_require_auth(api_client):
    # Phase 1A has no auth; the probe must be publicly reachable.
    response = api_client.get("/api/v1/health/")
    assert response.status_code == 200


def test_response_sets_x_frame_options_deny(api_client):
    # X_FRAME_OPTIONS="DENY" is only effective when XFrameOptionsMiddleware is
    # installed; verify a normal API response actually carries the header.
    response = api_client.get("/api/v1/health/")
    assert response.status_code == 200
    assert response["X-Frame-Options"] == "DENY"
