"""Production settings.

Selected with ``DJANGO_SETTINGS_MODULE=config.settings.prod``. Imports the shared
base and then enforces deployment requirements: a real secret key, an explicit
host allow-list, a PostgreSQL ``DATABASE_URL``, TLS/HSTS, and secure cookies.
See ``docs/PRODUCTION_DEPLOYMENT.md`` for the required environment and
deployment checks.
"""
from __future__ import annotations

import os

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F401,F403
from .base import env_bool

# Never run production with debug output or the shared development secret.
DEBUG = False

_secret = os.environ.get("SECRET_KEY", "").strip()
if not _secret or _secret == "dev-insecure-key-change-me-before-production":
    raise ImproperlyConfigured(
        "SECRET_KEY must be set to a strong, random value in production."
    )

# ``ALLOWED_HOSTS`` carries a localhost dev default in the base settings, so
# check the raw environment value here to force an explicit production allow-list.
if not os.environ.get("ALLOWED_HOSTS", "").strip():
    raise ImproperlyConfigured(
        "ALLOWED_HOSTS must be set to the deployed hostname(s) in production."
    )

if not CSRF_TRUSTED_ORIGINS:  # noqa: F405
    raise ImproperlyConfigured(
        "CSRF_TRUSTED_ORIGINS must be set (scheme://host) for cross-origin posts."
    )

# The base settings silently fall back to local SQLite when DATABASE_URL is
# absent, which is fine for development but never acceptable in production.
if not os.environ.get("DATABASE_URL", "").strip():
    raise ImproperlyConfigured(
        "DATABASE_URL must be set to a PostgreSQL URL in production."
    )

# ── TLS / HSTS ───────────────────────────────────────────────────────────────
# Redirect plain HTTP to HTTPS. If TLS is terminated at a reverse proxy, set
# TRUST_PROXY_SSL_HEADER=true *and* make sure the proxy strips any inbound
# X-Forwarded-Proto header; otherwise a client could spoof it.
SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", default=True)
SECURE_PROXY_SSL_HEADER = (
    ("HTTP_X_FORWARDED_PROTO", "https")
    if env_bool("TRUST_PROXY_SSL_HEADER", default=False)
    else None
)
SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", "31536000"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool(
    "SECURE_HSTS_INCLUDE_SUBDOMAINS", default=True
)
SECURE_HSTS_PRELOAD = env_bool("SECURE_HSTS_PRELOAD", default=True)

# ── Cookies ──────────────────────────────────────────────────────────────────
# All cookies must travel over HTTPS in production; the refresh cookie is
# already HttpOnly + SameSite from the base settings.
AUTH_COOKIE_SECURE = True  # noqa: F405
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True

# ── Logging ──────────────────────────────────────────────────────────────────
LOG_FORMAT = "json"
