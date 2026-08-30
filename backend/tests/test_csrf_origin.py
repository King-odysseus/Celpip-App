"""Regression tests for CSRF *origin* checking on the auth endpoints.

Distinct from ``test_accounts_api``'s double-submit token tests: these exercise
the ``Origin`` header check Django's CSRF middleware runs *before* the token
check. In development the SPA reaches Django through the Vite proxy
(``changeOrigin: true``), which forwards the browser's real ``Origin`` while
rewriting the Host. That makes Django compare the loopback Vite origin against
``CSRF_TRUSTED_ORIGINS``; if it is not trusted, every unsafe auth request fails
with ``403 permission_denied`` ("Origin checking failed") even with a valid
token.

The loopback dev origins must pass while an arbitrary origin stays rejected,
and the JSON error envelope must remain consistent.
"""
import pytest
from django.conf import settings

pytestmark = pytest.mark.django_db

REGISTER_URL = "/api/v1/auth/register/"
LOGIN_URL = "/api/v1/auth/login/"
REFRESH_URL = "/api/v1/auth/refresh/"
RECOVERY_URL = "/api/v1/auth/recovery-code/reset/"
CSRF_URL = "/api/v1/auth/csrf/"
REFRESH_COOKIE = settings.AUTH_REFRESH_COOKIE_NAME

LOOPBACK_ORIGINS = ["http://127.0.0.1:5173", "http://localhost:5173"]
ARBITRARY_ORIGIN = "http://evil.example"


def _bootstrap_token(csrf_client) -> str:
    """Prime the CSRF cookie and return the token the SPA would echo back."""
    csrf_client.get(CSRF_URL)
    return csrf_client.cookies["csrftoken"].value


@pytest.mark.parametrize("origin", LOOPBACK_ORIGINS)
def test_loopback_origins_pass_csrf_origin_check(csrf_client, origin):
    """With a valid token, both loopback Vite origins clear origin checking for
    register → login → refresh → recovery (i.e. never 403)."""
    token = _bootstrap_token(csrf_client)
    payload = {"identifier": "learner", "password": "secret1"}

    registered = csrf_client.post(
        REGISTER_URL, payload, format="json",
        HTTP_X_CSRFTOKEN=token, HTTP_ORIGIN=origin,
    )
    assert registered.status_code == 201, registered.content
    recovery_code = registered.json()["recovery_code"]

    # Refresh acts on the refresh cookie register just set; must rotate cleanly.
    refreshed = csrf_client.post(
        REFRESH_URL, HTTP_X_CSRFTOKEN=token, HTTP_ORIGIN=origin
    )
    assert refreshed.status_code == 200, refreshed.content

    # Drop the refresh cookie so login is exercised as a fresh sign-in.
    csrf_client.cookies.pop(REFRESH_COOKIE, None)
    logged_in = csrf_client.post(
        LOGIN_URL, payload, format="json",
        HTTP_X_CSRFTOKEN=token, HTTP_ORIGIN=origin,
    )
    assert logged_in.status_code == 200, logged_in.content

    recovered = csrf_client.post(
        RECOVERY_URL,
        {
            "identifier": "learner",
            "recovery_code": recovery_code,
            "new_password": "brandnew1",
        },
        format="json",
        HTTP_X_CSRFTOKEN=token, HTTP_ORIGIN=origin,
    )
    assert recovered.status_code == 200, recovered.content


@pytest.mark.parametrize("url", [REGISTER_URL, LOGIN_URL, REFRESH_URL, RECOVERY_URL])
def test_arbitrary_origin_is_rejected_with_envelope(csrf_client, url):
    """An untrusted origin fails origin checking even with a valid token, and
    the response keeps the platform's consistent JSON error envelope."""
    token = _bootstrap_token(csrf_client)

    blocked = csrf_client.post(
        url,
        {"identifier": "learner", "password": "secret1"},
        format="json",
        HTTP_X_CSRFTOKEN=token, HTTP_ORIGIN=ARBITRARY_ORIGIN,
    )
    assert blocked.status_code == 403, blocked.content
    body = blocked.json()
    assert body["code"] == "permission_denied"
    assert set(body) == {"code", "message", "fields"}
