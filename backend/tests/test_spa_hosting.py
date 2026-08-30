"""Same-origin SPA hosting: the catch-all fallback and its guard rails.

These exercise ``apps.core.views.spa_index`` — the last URL pattern that serves
the built single-page app for client-side deep links while refusing to shadow
the API, admin, static, or private-media routes.
"""
from pathlib import Path

import pytest
from django.test import override_settings

INDEX_HTML = "<!doctype html><html><body><div id='root'></div></body></html>"


@pytest.fixture
def built_spa(tmp_path: Path):
    """A temporary SPA build directory containing an ``index.html``."""
    index = tmp_path / "index.html"
    index.write_text(INDEX_HTML, encoding="utf-8")
    with override_settings(SPA_ROOT=tmp_path, SPA_INDEX_FILE=index):
        yield index


def test_deep_route_serves_index(client, built_spa):
    # A client-side route with no matching backend URL returns the SPA shell.
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert response["Content-Type"] == "text/html"
    body = b"".join(response.streaming_content).decode("utf-8")
    assert body == INDEX_HTML


def test_root_serves_index(client, built_spa):
    response = client.get("/")
    assert response.status_code == 200
    body = b"".join(response.streaming_content).decode("utf-8")
    assert body == INDEX_HTML


def test_nested_deep_route_serves_index(client, built_spa):
    # Deep links several segments in still resolve to the shell.
    response = client.get("/mocks/123/review")
    assert response.status_code == 200


def test_api_health_is_not_shadowed(client, built_spa):
    # Even with a built SPA present, the real API keeps answering with JSON.
    response = client.get("/api/v1/health/")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "celpip-backend"


def test_unknown_api_path_stays_404(client, built_spa):
    # A miss under /api/ must be a genuine 404, never the SPA HTML shell.
    response = client.get("/api/v1/does-not-exist/")
    assert response.status_code == 404


def test_admin_prefix_is_not_shadowed(client, built_spa):
    # /admin/ is reserved: the admin app handles it (an unauthenticated hit
    # redirects to the admin login) instead of the SPA shell being served.
    response = client.get("/admin/nope/")
    assert response.status_code == 302
    assert response["Location"].startswith("/admin/login/")


def test_missing_asset_returns_404_not_index(client, built_spa):
    # Asset-looking paths (a dot in the final segment) must 404 when absent
    # instead of being answered with the HTML shell.
    response = client.get("/assets/index-deadbeef.js")
    assert response.status_code == 404


def test_static_prefix_is_not_shadowed(client, built_spa):
    response = client.get("/static/missing.css")
    assert response.status_code == 404


def test_no_build_present_routes_404():
    # Without a built SPA (the default in dev/tests), deep links 404 exactly as
    # they did before same-origin hosting existed.
    from django.conf import settings
    from django.test import Client

    missing = settings.BASE_DIR / "spa" / "does-not-exist" / "index.html"
    with override_settings(SPA_INDEX_FILE=missing):
        response = Client().get("/dashboard")
    assert response.status_code == 404
