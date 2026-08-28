"""JWT issuance/rotation and the HttpOnly refresh-cookie helpers.

The access token is short-lived and returned in the JSON body for the SPA to
hold in memory. The refresh token is long-lived and only ever travels in an
HttpOnly cookie scoped to the auth endpoints, so page JavaScript cannot read it.
"""
from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings
from rest_framework.authentication import SessionAuthentication
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User


@dataclass(frozen=True)
class TokenPair:
    access: str
    refresh: str


def issue_tokens_for_user(user: User) -> TokenPair:
    refresh = RefreshToken.for_user(user)
    return TokenPair(access=str(refresh.access_token), refresh=str(refresh))


def rotate_refresh_token(refresh_token: str) -> TokenPair:
    """Validate a refresh token, blacklist it, and mint a rotated pair.

    Relies on SimpleJWT's ``ROTATE_REFRESH_TOKENS`` and
    ``BLACKLIST_AFTER_ROTATION`` settings, so the old token cannot be reused.
    Raises ``TokenError`` on an invalid, expired, or blacklisted token.
    """
    serializer = TokenRefreshSerializer(data={"refresh": refresh_token})
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    return TokenPair(access=data["access"], refresh=data["refresh"])


def blacklist_refresh_token(refresh_token: str) -> None:
    """Revoke a refresh token so it can never be rotated again."""
    RefreshToken(refresh_token).blacklist()


# ── Refresh cookie ───────────────────────────────────────────────────────────
def set_refresh_cookie(response: Response, refresh_token: str) -> None:
    max_age = int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds())
    response.set_cookie(
        settings.AUTH_REFRESH_COOKIE_NAME,
        refresh_token,
        max_age=max_age,
        httponly=True,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite=settings.AUTH_COOKIE_SAMESITE,
        path=settings.AUTH_COOKIE_PATH,
    )


def clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        settings.AUTH_REFRESH_COOKIE_NAME,
        path=settings.AUTH_COOKIE_PATH,
        samesite=settings.AUTH_COOKIE_SAMESITE,
    )


def read_refresh_cookie(request: Request) -> str | None:
    return request.COOKIES.get(settings.AUTH_REFRESH_COOKIE_NAME)


# ── CSRF for cookie-authenticated, state-changing endpoints ──────────────────
_csrf_checker = SessionAuthentication()


def enforce_csrf(request: Request) -> None:
    """Reject the request unless it carries a valid CSRF token.

    Applied to refresh/logout, which act on the refresh cookie the browser
    sends automatically. Raises ``rest_framework.exceptions.PermissionDenied``
    when the double-submit CSRF check fails.
    """
    _csrf_checker.enforce_csrf(request)
