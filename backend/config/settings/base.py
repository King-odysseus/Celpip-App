"""Base Django settings shared by every environment.

Everything that varies between machines or deployments is read from the
environment. Environment-specific modules (``dev``, and later ``prod``) import
from here and override only what they must.
"""
from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path

import dj_database_url
from corsheaders.defaults import default_headers

# backend/config/settings/base.py -> parents[2] == backend/
BASE_DIR = Path(__file__).resolve().parents[2]


def env_bool(name: str, default: bool = False) -> bool:
    """Read a boolean from the environment ("true"/"1"/"yes" are truthy)."""
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str = "") -> list[str]:
    """Read a comma-separated list from the environment."""
    raw = os.environ.get(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


# ── Core ────────────────────────────────────────────────────────────────────
# A development fallback keeps the app runnable without configuration; the
# production settings module must require a real SECRET_KEY.
SECRET_KEY = os.environ.get(
    "SECRET_KEY", "dev-insecure-key-change-me-before-production"
)

DEBUG = env_bool("DEBUG", default=False)

ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", default="localhost,127.0.0.1")

# ── Applications ────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.admin",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    # Local
    "apps.core",
    "apps.accounts",
    "apps.content",
    "apps.assessments",
    "apps.media_assets",
    "apps.ai_services",
    "apps.learning",
    "apps.mocks",
]

# The custom user model must be declared before its first migration runs, and
# before any domain app references it.
AUTH_USER_MODEL = "accounts.User"

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    # WhiteNoise serves Django's collected /static/ assets and (when a built SPA
    # is present) the SPA's hashed files at the site root. It must sit directly
    # after SecurityMiddleware and before everything else so it can short-circuit
    # static requests without running the rest of the stack. It is harmless in
    # development: with nothing collected it simply passes requests through.
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.core.middleware.RequestCorrelationMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ── Database ────────────────────────────────────────────────────────────────
# Use DATABASE_URL when provided (e.g. PostgreSQL). When it is absent, fall
# back automatically to a local SQLite file so development and the test suite
# work with zero configuration. PostgreSQL support is ready for later phases.
DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()

if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.parse(DATABASE_URL, conn_max_age=600),
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ── Authentication / password hashing ───────────────────────────────────────
# Argon2 is the preferred hasher (loose registration must not mean weak
# storage). The remaining hashers let Django verify and upgrade legacy hashes.
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]

# The six-character minimum is enforced in the registration service; Django's
# heavier validators are intentionally not layered on top for launch UX.
AUTH_PASSWORD_VALIDATORS: list[dict] = []

# ── REST framework ──────────────────────────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": (
        "rest_framework.pagination.PageNumberPagination"
    ),
    "PAGE_SIZE": 20,
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": os.environ.get("THROTTLE_ANON", "60/min"),
        "user": os.environ.get("THROTTLE_USER", "240/min"),
        "auth_login": os.environ.get("THROTTLE_AUTH_LOGIN", "10/min"),
        "auth_register": os.environ.get("THROTTLE_AUTH_REGISTER", "10/hour"),
        "auth_recovery": os.environ.get("THROTTLE_AUTH_RECOVERY", "10/hour"),
    },
    "EXCEPTION_HANDLER": "apps.core.exceptions.exception_handler",
}

# ── SimpleJWT ────────────────────────────────────────────────────────────────
# Short-lived access token in JSON (held in memory by the SPA); rotating
# refresh token in an HttpOnly cookie, with old tokens blacklisted on rotation.
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "CHECK_REVOKE_TOKEN": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# ── Auth cookies / CSRF ──────────────────────────────────────────────────────
# The refresh cookie is scoped to the auth endpoints so it is only sent where
# it is needed. "Secure" defaults to on outside DEBUG; dev over http keeps it
# off so local cookies work. Same-origin deployment uses SameSite=Lax.
AUTH_REFRESH_COOKIE_NAME = os.environ.get("AUTH_REFRESH_COOKIE_NAME", "celpip_refresh")
AUTH_COOKIE_PATH = os.environ.get("AUTH_COOKIE_PATH", "/api/v1/auth")
AUTH_COOKIE_SAMESITE = os.environ.get("AUTH_COOKIE_SAMESITE", "Lax")
AUTH_COOKIE_SECURE = env_bool("AUTH_COOKIE_SECURE", default=not DEBUG)

# CSRF cookie must be readable by JS so the SPA can echo it in the header for
# unsafe authentication endpoints.
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = AUTH_COOKIE_SAMESITE
CSRF_COOKIE_SECURE = AUTH_COOKIE_SECURE
SESSION_COOKIE_SECURE = AUTH_COOKIE_SECURE
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS")

# ── CORS ────────────────────────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS = env_list(
    "CORS_ALLOWED_ORIGINS",
    default="http://localhost:5173,http://127.0.0.1:5173",
)
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = (*default_headers, "idempotency-key", "x-guest-token")

# ── Security headers ────────────────────────────────────────────────────────
# Applied by SecurityMiddleware. These defaults are safe in every environment;
# the production module additionally enables TLS/HSTS. Deny framing outright,
# and keep the referrer policy conservative. None of these affect the SPA's
# same-origin (or proxied) dev flow.
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"

# ── Request / correlation IDs ────────────────────────────────────────────────
# Header names surfaced on responses and read from inbound requests. Logging is
# tagged with these IDs (see apps.core.logging) but never with bodies/audio.
REQUEST_ID_HEADER = os.environ.get("REQUEST_ID_HEADER", "X-Request-ID")
CORRELATION_ID_HEADER = os.environ.get("CORRELATION_ID_HEADER", "X-Correlation-ID")

# ── Structured logging ───────────────────────────────────────────────────────
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
LOG_FORMAT = os.environ.get("LOG_FORMAT", "plain").strip().lower()

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "correlation": {"()": "apps.core.logging.CorrelationFilter"},
    },
    "formatters": {
        "plain": {
            "format": (
                "[{asctime}] {levelname} {name} "
                "request_id={request_id} correlation_id={correlation_id} "
                "{message}"
            ),
            "style": "{",
        },
        "json": {"()": "apps.core.logging.JsonFormatter"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json" if LOG_FORMAT == "json" else "plain",
            "filters": ["correlation"],
        },
    },
    "root": {"handlers": ["console"], "level": LOG_LEVEL},
    "loggers": {
        "django": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False},
        "django.request": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        "django.server": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        "apps": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False},
    },
}

# ── Internationalisation ────────────────────────────────────────────────────
LANGUAGE_CODE = "en-ca"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ── Static files ────────────────────────────────────────────────────────────
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
PRIVATE_MEDIA_ROOT = Path(
    os.environ.get("PRIVATE_MEDIA_ROOT") or BASE_DIR / "private_media"
)

# ── Single-service SPA hosting ───────────────────────────────────────────────
# In the container build, the compiled Vite bundle is copied to ``SPA_ROOT``.
# When an ``index.html`` is present there, WhiteNoise serves the SPA's hashed
# files (``/assets/…``, ``/favicon.svg`` …) at the site root and the catch-all
# view (see ``config.urls``) returns ``index.html`` for client-side deep links.
# When it is absent — local development, tests, the API-only dev server — none
# of this activates and the SPA is served by the Vite dev server as before.
SPA_ROOT = Path(os.environ.get("SPA_ROOT") or BASE_DIR / "spa")
SPA_INDEX_FILE = SPA_ROOT / "index.html"

# WhiteNoise serves the SPA files at the root only when the build exists, so a
# missing bundle never turns every request into a WhiteNoise 404.
if SPA_INDEX_FILE.is_file():
    WHITENOISE_ROOT = str(SPA_ROOT)
# Serve ``index.html`` for directory requests (i.e. ``GET /``) from WHITENOISE_ROOT.
WHITENOISE_INDEX_FILE = True

# Default static storage. Production swaps this for WhiteNoise's compressed,
# hash-manifest storage (see ``config.settings.prod``); development keeps the
# plain filesystem backend so ``runserver`` works without a collectstatic pass.
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
    },
}

# Application metadata surfaced by the health endpoint.
SERVICE_NAME = "celpip-backend"
SERVICE_VERSION = "0.1.0"

# ── Audited AI services ──────────────────────────────────────────────────
# The fake provider keeps development/tests deterministic. Production can
# switch to OpenAI without changing domain code. API responses are never
# treated as official CELPIP scores and generated content remains a draft.
AI_PROVIDER = os.environ.get("AI_PROVIDER", "fake").strip().lower()
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()
OPENAI_TEXT_MODEL = os.environ.get("OPENAI_TEXT_MODEL", "gpt-5.6-luna").strip()
OPENAI_TRANSCRIBE_MODEL = os.environ.get(
    "OPENAI_TRANSCRIBE_MODEL", "gpt-4o-mini-transcribe"
).strip()
OPENAI_TTS_MODEL = os.environ.get("OPENAI_TTS_MODEL", "gpt-4o-mini-tts").strip()
OPENAI_IMAGE_MODEL = os.environ.get("OPENAI_IMAGE_MODEL", "gpt-image-2").strip()
AI_MAX_ATTEMPTS = int(os.environ.get("AI_MAX_ATTEMPTS", "3"))
AI_JOB_POLL_SECONDS = float(os.environ.get("AI_JOB_POLL_SECONDS", "2"))

# ── Listening audio synthesis (text-to-speech) ──────────────────────────────
# Stored Listening audio is generated once and reused. Regeneration tries these
# providers in order until one returns a valid WAV. This order is deliberately
# independent of AI_PROVIDER: general AI evaluation can run on the fake provider
# while listening audio is still produced by a live speech vendor. "local" is
# the terminal fallback that retains the existing validated recording so a
# working file is never destroyed when every upstream provider fails.
LISTENING_TTS_PROVIDER_ORDER = env_list(
    "LISTENING_TTS_PROVIDER_ORDER", default="openai,azure,local"
)
# Two distinct OpenAI voices give dialogue scripts two clean speakers. Server
# side OPENAI_API_KEY and OPENAI_TTS_MODEL (above) are reused; keys never leave
# the server or appear in provenance/metadata.
LISTENING_OPENAI_VOICES = env_list(
    "LISTENING_OPENAI_VOICES", default="alloy,onyx"
)
# Azure Speech neural TTS. Canadian English voices by default.
AZURE_SPEECH_KEY = os.environ.get("AZURE_SPEECH_KEY", "").strip()
AZURE_SPEECH_REGION = os.environ.get("AZURE_SPEECH_REGION", "").strip()
LISTENING_AZURE_VOICES = env_list(
    "LISTENING_AZURE_VOICES", default="en-CA-ClaraNeural,en-CA-LiamNeural"
)

# Per-provider audio renditions (generate_listening_renditions) reuse the same
# server-side keys/models/voices above, but store each output at a separate
# private path (listening_renditions/{provider}/{canonical-id}.wav) so the
# canonical MediaAsset WAV is never replaced. Renditions support openai/azure
# only and never fall back to the local provider.
