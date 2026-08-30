"""Deployment-facing settings: WhiteNoise middleware and static storage.

The production single-service image relies on WhiteNoise both for the collected
``/static/`` assets and for hosting the SPA bundle at the site root. These tests
lock in the middleware placement (shared by every environment) and the
production-only compressed, hashed static storage.
"""
import importlib
import sys

import pytest

PROD_MODULE = "config.settings.prod"

_PROD_ENV_KEYS = (
    "SECRET_KEY",
    "ALLOWED_HOSTS",
    "CSRF_TRUSTED_ORIGINS",
    "DATABASE_URL",
)


@pytest.fixture(autouse=True)
def _reset_prod_cache():
    sys.modules.pop(PROD_MODULE, None)
    yield
    sys.modules.pop(PROD_MODULE, None)


def _load_prod(monkeypatch):
    import config.settings.base as base

    for key in _PROD_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("SECRET_KEY", "a" * 50)
    monkeypatch.setenv("ALLOWED_HOSTS", "app.example.com")
    monkeypatch.setenv("CSRF_TRUSTED_ORIGINS", "https://app.example.com")
    monkeypatch.setenv("DATABASE_URL", "postgres://u:p@localhost:5432/celpip")
    importlib.reload(base)
    sys.modules.pop(PROD_MODULE, None)
    return importlib.import_module(PROD_MODULE)


def test_whitenoise_middleware_directly_after_security():
    from django.conf import settings

    mw = settings.MIDDLEWARE
    security = "django.middleware.security.SecurityMiddleware"
    whitenoise = "whitenoise.middleware.WhiteNoiseMiddleware"
    assert whitenoise in mw
    assert mw.index(whitenoise) == mw.index(security) + 1


def test_dev_uses_plain_static_storage():
    # Development must not require a collectstatic manifest to serve pages.
    from django.conf import settings

    assert settings.STORAGES["staticfiles"]["BACKEND"] == (
        "django.contrib.staticfiles.storage.StaticFilesStorage"
    )


def test_prod_uses_whitenoise_compressed_manifest_storage(monkeypatch):
    prod = _load_prod(monkeypatch)
    assert prod.STORAGES["staticfiles"]["BACKEND"] == (
        "whitenoise.storage.CompressedManifestStaticFilesStorage"
    )


def test_prod_exempts_health_from_ssl_redirect(monkeypatch):
    # The internal HTTP health probe must not be answered with a 301.
    prod = _load_prod(monkeypatch)
    assert prod.SECURE_SSL_REDIRECT is True
    assert r"^api/v1/health/$" in prod.SECURE_REDIRECT_EXEMPT
