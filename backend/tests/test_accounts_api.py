"""API tests: register, login, refresh, logout, recovery, profile, throttling,
cookie behaviour, and CSRF protection."""
import pytest
from django.conf import settings

from apps.accounts.models import RecoveryCode, User
from apps.accounts.throttling import LoginRateThrottle

pytestmark = pytest.mark.django_db

REGISTER_URL = "/api/v1/auth/register/"
LOGIN_URL = "/api/v1/auth/login/"
REFRESH_URL = "/api/v1/auth/refresh/"
LOGOUT_URL = "/api/v1/auth/logout/"
RECOVERY_URL = "/api/v1/auth/recovery-code/reset/"
CSRF_URL = "/api/v1/auth/csrf/"
ME_URL = "/api/v1/me/"
PROFILE_URL = "/api/v1/me/profile/"
REFRESH_COOKIE = settings.AUTH_REFRESH_COOKIE_NAME


# ── Registration ─────────────────────────────────────────────────────────────
def test_register_returns_access_recovery_and_sets_cookie(api_client):
    resp = api_client.post(
        REGISTER_URL, {"identifier": "learner", "password": "secret1"}, format="json"
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["access"]
    assert body["recovery_code"]
    assert body["user"]["identifier"] == "learner"
    # Refresh token is delivered as an HttpOnly cookie, never in the body.
    assert "refresh" not in body
    cookie = resp.cookies[REFRESH_COOKIE]
    assert cookie["httponly"]
    assert cookie["path"] == settings.AUTH_COOKIE_PATH
    assert User.objects.filter(identifier="learner").exists()


def test_register_rejects_short_password(api_client):
    resp = api_client.post(
        REGISTER_URL, {"identifier": "learner", "password": "12345"}, format="json"
    )
    assert resp.status_code == 400
    assert not User.objects.filter(identifier="learner").exists()


def test_register_requires_exactly_identifier_and_password(api_client):
    resp = api_client.post(REGISTER_URL, {"identifier": "learner"}, format="json")
    assert resp.status_code == 400
    assert resp.json()["code"] == "invalid_input"


def test_register_duplicate_identifier_conflicts(api_client):
    api_client.post(
        REGISTER_URL, {"identifier": "learner", "password": "secret1"}, format="json"
    )
    resp = api_client.post(
        REGISTER_URL, {"identifier": "LEARNER", "password": "secret1"}, format="json"
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "identifier_taken"


# ── Login ────────────────────────────────────────────────────────────────────
def test_login_succeeds_and_sets_cookie(api_client):
    User.objects.create_user(identifier="learner", password="secret1")
    resp = api_client.post(
        LOGIN_URL, {"identifier": "Learner", "password": "secret1"}, format="json"
    )
    assert resp.status_code == 200
    assert resp.json()["access"]
    assert REFRESH_COOKIE in resp.cookies


def test_login_wrong_password_is_generic(api_client):
    User.objects.create_user(identifier="learner", password="secret1")
    resp = api_client.post(
        LOGIN_URL, {"identifier": "learner", "password": "wrong-one"}, format="json"
    )
    assert resp.status_code == 401
    assert resp.json()["code"] == "invalid_credentials"


def test_login_unknown_user_uses_same_error(api_client):
    resp = api_client.post(
        LOGIN_URL, {"identifier": "ghost", "password": "whatever"}, format="json"
    )
    assert resp.status_code == 401
    assert resp.json()["code"] == "invalid_credentials"


# ── Refresh / logout ─────────────────────────────────────────────────────────
def test_refresh_rotates_and_returns_new_access(api_client):
    api_client.post(
        REGISTER_URL, {"identifier": "learner", "password": "secret1"}, format="json"
    )
    first_cookie = api_client.cookies[REFRESH_COOKIE].value
    resp = api_client.post(REFRESH_URL)
    assert resp.status_code == 200
    assert resp.json()["access"]
    rotated = resp.cookies[REFRESH_COOKIE].value
    assert rotated != first_cookie


def test_old_refresh_token_is_blacklisted_after_rotation(api_client):
    api_client.post(
        REGISTER_URL, {"identifier": "learner", "password": "secret1"}, format="json"
    )
    old_cookie = api_client.cookies[REFRESH_COOKIE].value
    api_client.post(REFRESH_URL)  # rotates + blacklists old
    # Replay the original token: it must now be rejected.
    api_client.cookies[REFRESH_COOKIE] = old_cookie
    resp = api_client.post(REFRESH_URL)
    assert resp.status_code == 401


def test_refresh_without_cookie_is_unauthorized(api_client):
    resp = api_client.post(REFRESH_URL)
    assert resp.status_code == 401
    assert resp.json()["code"] == "no_refresh_token"


def test_logout_revokes_refresh_and_clears_cookie(api_client):
    api_client.post(
        REGISTER_URL, {"identifier": "learner", "password": "secret1"}, format="json"
    )
    resp = api_client.post(LOGOUT_URL)
    assert resp.status_code == 205
    # Cookie is cleared (expired) on the response.
    assert resp.cookies[REFRESH_COOKIE].value == ""
    # The revoked token can no longer be refreshed.
    retry = api_client.post(REFRESH_URL)
    assert retry.status_code == 401


# ── CSRF protection for cookie-mutating endpoints ────────────────────────────
def test_refresh_requires_csrf_when_enforced(csrf_client):
    csrf_client.get(CSRF_URL)
    token = csrf_client.cookies["csrftoken"].value
    csrf_client.post(
        REGISTER_URL,
        {"identifier": "learner", "password": "secret1"},
        format="json",
        HTTP_X_CSRFTOKEN=token,
    )
    # No CSRF header → rejected.
    blocked = csrf_client.post(REFRESH_URL)
    assert blocked.status_code == 403

    # Echo the bootstrapped token in the header → accepted.
    allowed = csrf_client.post(REFRESH_URL, HTTP_X_CSRFTOKEN=token)
    assert allowed.status_code == 200


def test_register_login_recovery_and_logout_require_csrf(csrf_client):
    register_payload = {"identifier": "learner", "password": "secret1"}
    assert csrf_client.post(REGISTER_URL, register_payload, format="json").status_code == 403

    csrf_client.get(CSRF_URL)
    token = csrf_client.cookies["csrftoken"].value
    registered = csrf_client.post(
        REGISTER_URL,
        register_payload,
        format="json",
        HTTP_X_CSRFTOKEN=token,
    )
    assert registered.status_code == 201
    recovery_code = registered.json()["recovery_code"]

    csrf_client.cookies.pop(REFRESH_COOKIE, None)
    assert csrf_client.post(LOGIN_URL, register_payload, format="json").status_code == 403
    logged_in = csrf_client.post(
        LOGIN_URL,
        register_payload,
        format="json",
        HTTP_X_CSRFTOKEN=token,
    )
    assert logged_in.status_code == 200

    recovery_payload = {
        "identifier": "learner",
        "recovery_code": recovery_code,
        "new_password": "brandnew1",
    }
    assert csrf_client.post(RECOVERY_URL, recovery_payload, format="json").status_code == 403
    recovered = csrf_client.post(
        RECOVERY_URL,
        recovery_payload,
        format="json",
        HTTP_X_CSRFTOKEN=token,
    )
    assert recovered.status_code == 200

    assert csrf_client.post(LOGOUT_URL).status_code == 403
    assert csrf_client.post(LOGOUT_URL, HTTP_X_CSRFTOKEN=token).status_code == 205


# ── Recovery-code reset ──────────────────────────────────────────────────────
def test_recovery_reset_changes_password_and_rotates_code(api_client):
    reg = api_client.post(
        REGISTER_URL, {"identifier": "learner", "password": "secret1"}, format="json"
    )
    code = reg.json()["recovery_code"]

    resp = api_client.post(
        RECOVERY_URL,
        {"identifier": "learner", "recovery_code": code, "new_password": "brandnew1"},
        format="json",
    )
    assert resp.status_code == 200
    new_code = resp.json()["recovery_code"]
    assert new_code and new_code != code

    user = User.objects.get(identifier="learner")
    assert user.check_password("brandnew1")

    # The consumed code cannot be reused.
    replay = api_client.post(
        RECOVERY_URL,
        {"identifier": "learner", "recovery_code": code, "new_password": "another11"},
        format="json",
    )
    assert replay.status_code == 400


def test_recovery_reset_revokes_existing_refresh_and_access_tokens(api_client):
    reg = api_client.post(
        REGISTER_URL, {"identifier": "learner", "password": "secret1"}, format="json"
    )
    recovery_code = reg.json()["recovery_code"]
    old_access = reg.json()["access"]
    old_refresh = api_client.cookies[REFRESH_COOKIE].value

    reset = api_client.post(
        RECOVERY_URL,
        {
            "identifier": "learner",
            "recovery_code": recovery_code,
            "new_password": "brandnew1",
        },
        format="json",
    )
    assert reset.status_code == 200

    api_client.cookies[REFRESH_COOKIE] = old_refresh
    assert api_client.post(REFRESH_URL).status_code == 401
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {old_access}")
    assert api_client.get(ME_URL).status_code == 401


def test_recovery_reset_wrong_code_is_generic(api_client):
    api_client.post(
        REGISTER_URL, {"identifier": "learner", "password": "secret1"}, format="json"
    )
    resp = api_client.post(
        RECOVERY_URL,
        {"identifier": "learner", "recovery_code": "nope", "new_password": "brandnew1"},
        format="json",
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "invalid_credentials"
    assert RecoveryCode.objects.get(user__identifier="learner").used_at is None


# ── Profile / me (ownership) ─────────────────────────────────────────────────
def _auth(api_client, identifier="learner", password="secret1"):
    reg = api_client.post(
        REGISTER_URL, {"identifier": identifier, "password": password}, format="json"
    )
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {reg.json()['access']}")


def test_me_requires_authentication(api_client):
    assert api_client.get(ME_URL).status_code == 401


def test_profile_get_and_patch_scoped_to_owner(api_client):
    _auth(api_client)
    get_resp = api_client.get(PROFILE_URL)
    assert get_resp.status_code == 200
    assert get_resp.json()["identifier"] == "learner"

    patch = api_client.patch(
        PROFILE_URL,
        {
            "exam_date": "2026-10-10",
            "target_level": 8,
            "target_writing": 10,
            "daily_minutes": 45,
            "preferred_weekdays": [1, 3, 5],
            "timezone": "America/Vancouver",
        },
        format="json",
    )
    assert patch.status_code == 200
    body = patch.json()
    assert body["exam_date"] == "2026-10-10"
    assert body["target_level"] == 8
    assert body["target_writing"] == 10
    assert body["preferred_weekdays"] == [1, 3, 5]


def test_profile_defaults_narration_voice_to_automatic(api_client):
    _auth(api_client)
    body = api_client.get(PROFILE_URL).json()
    assert body["practice_narration_voice"] == "automatic"


def test_profile_accepts_valid_narration_voice(api_client):
    _auth(api_client)
    resp = api_client.patch(
        PROFILE_URL, {"practice_narration_voice": "voice_2"}, format="json"
    )
    assert resp.status_code == 200
    assert resp.json()["practice_narration_voice"] == "voice_2"


def test_profile_rejects_unknown_narration_voice(api_client):
    _auth(api_client)
    resp = api_client.patch(
        PROFILE_URL, {"practice_narration_voice": "provider:openai"}, format="json"
    )
    assert resp.status_code == 400
    assert "practice_narration_voice" in resp.json()["fields"]


def test_profile_rejects_out_of_range_target(api_client):
    _auth(api_client)
    resp = api_client.patch(PROFILE_URL, {"target_level": 99}, format="json")
    assert resp.status_code == 400


def test_profile_rejects_bad_weekdays(api_client):
    _auth(api_client)
    resp = api_client.patch(PROFILE_URL, {"preferred_weekdays": [0, 8]}, format="json")
    assert resp.status_code == 400


def test_profile_rejects_unknown_timezone(api_client):
    _auth(api_client)
    resp = api_client.patch(
        PROFILE_URL, {"timezone": "Mars/Olympus_Mons"}, format="json"
    )
    assert resp.status_code == 400
    assert "timezone" in resp.json()["fields"]


# ── Throttling ───────────────────────────────────────────────────────────────
def test_login_is_throttled_by_identifier(api_client, monkeypatch):
    User.objects.create_user(identifier="learner", password="secret1")
    # DRF snapshots THROTTLE_RATES on the class at import time, so patch it there.
    monkeypatch.setattr(
        LoginRateThrottle,
        "THROTTLE_RATES",
        {**LoginRateThrottle.THROTTLE_RATES, "auth_login": "3/min"},
    )
    statuses = [
        api_client.post(
            LOGIN_URL,
            {"identifier": "learner", "password": "wrong-one"},
            format="json",
        ).status_code
        for _ in range(4)
    ]
    assert statuses[:3] == [401, 401, 401]
    assert statuses[3] == 429
