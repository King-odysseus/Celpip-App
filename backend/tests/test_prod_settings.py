"""Production settings module: required values and security defaults."""
import importlib
import sys

import pytest
from django.core.exceptions import ImproperlyConfigured

PROD_MODULE = "config.settings.prod"

# Env vars that prod.py reads directly; cleared before each load so ambient
# developer environment variables cannot mask missing-value failures.
_PROD_ENV_KEYS = (
    "SECRET_KEY",
    "ALLOWED_HOSTS",
    "CSRF_TRUSTED_ORIGINS",
    "DATABASE_URL",
    "SECURE_SSL_REDIRECT",
    "TRUST_PROXY_SSL_HEADER",
    "SECURE_HSTS_SECONDS",
    "SECURE_HSTS_INCLUDE_SUBDOMAINS",
    "SECURE_HSTS_PRELOAD",
    "LOG_FORMAT",
)


@pytest.fixture(autouse=True)
def _reset_prod_cache():
    sys.modules.pop(PROD_MODULE, None)
    yield
    sys.modules.pop(PROD_MODULE, None)


def _load_prod(monkeypatch, **env):
    import config.settings.base as base

    for key in _PROD_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    importlib.reload(base)
    sys.modules.pop(PROD_MODULE, None)
    return importlib.import_module(PROD_MODULE)


def _valid_env():
    return {
        "SECRET_KEY": "a" * 50,
        "ALLOWED_HOSTS": "app.example.com",
        "CSRF_TRUSTED_ORIGINS": "https://app.example.com",
        "DATABASE_URL": "postgres://user:pass@localhost:5432/celpip",
    }


def test_prod_requires_a_real_secret_key(monkeypatch):
    env = {k: v for k, v in _valid_env().items() if k != "SECRET_KEY"}
    with pytest.raises(ImproperlyConfigured, match="SECRET_KEY"):
        _load_prod(monkeypatch, **env)


def test_prod_rejects_the_development_secret(monkeypatch):
    env = _valid_env()
    env["SECRET_KEY"] = "dev-insecure-key-change-me-before-production"
    with pytest.raises(ImproperlyConfigured, match="SECRET_KEY"):
        _load_prod(monkeypatch, **env)


def test_prod_requires_allowed_hosts_and_trusted_origins(monkeypatch):
    env = {k: v for k, v in _valid_env().items() if k != "ALLOWED_HOSTS"}
    with pytest.raises(ImproperlyConfigured, match="ALLOWED_HOSTS"):
        _load_prod(monkeypatch, **env)

    env = {k: v for k, v in _valid_env().items() if k != "CSRF_TRUSTED_ORIGINS"}
    with pytest.raises(ImproperlyConfigured, match="CSRF_TRUSTED_ORIGINS"):
        _load_prod(monkeypatch, **env)


def test_prod_requires_database_url(monkeypatch):
    env = {k: v for k, v in _valid_env().items() if k != "DATABASE_URL"}
    with pytest.raises(ImproperlyConfigured, match="DATABASE_URL"):
        _load_prod(monkeypatch, **env)

    # A whitespace-only value is also rejected, not just an unset variable.
    env = _valid_env()
    env["DATABASE_URL"] = "   "
    with pytest.raises(ImproperlyConfigured, match="DATABASE_URL"):
        _load_prod(monkeypatch, **env)


def test_prod_applies_security_defaults(monkeypatch):
    prod = _load_prod(monkeypatch, **_valid_env())

    assert prod.DEBUG is False
    assert prod.SECURE_SSL_REDIRECT is True
    assert prod.SECURE_PROXY_SSL_HEADER is None
    assert prod.SECURE_HSTS_SECONDS == 31536000
    assert prod.SECURE_HSTS_INCLUDE_SUBDOMAINS is True
    assert prod.SECURE_HSTS_PRELOAD is True
    assert prod.AUTH_COOKIE_SECURE is True
    assert prod.CSRF_COOKIE_SECURE is True
    assert prod.SESSION_COOKIE_SECURE is True
    assert prod.LOG_FORMAT == "json"


def test_prod_trusts_proxy_ssl_header_only_when_enabled(monkeypatch):
    prod = _load_prod(
        monkeypatch, **_valid_env(), TRUST_PROXY_SSL_HEADER="true"
    )
    assert prod.SECURE_PROXY_SSL_HEADER == ("HTTP_X_FORWARDED_PROTO", "https")
