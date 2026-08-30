"""Tests for environment-driven settings behaviour."""
import importlib

from django.conf import settings

from config.settings import base


def test_sqlite_fallback_when_no_database_url(monkeypatch):
    # With no DATABASE_URL, the loader must select the local SQLite engine.
    monkeypatch.delenv("DATABASE_URL", raising=False)
    reloaded = importlib.reload(base)

    engine = reloaded.DATABASES["default"]["ENGINE"]
    assert engine == "django.db.backends.sqlite3"


def test_database_url_selects_postgres(monkeypatch):
    monkeypatch.setenv(
        "DATABASE_URL", "postgres://user:pass@localhost:5432/celpip"
    )
    reloaded = importlib.reload(base)

    engine = reloaded.DATABASES["default"]["ENGINE"]
    assert engine == "django.db.backends.postgresql"

    # Restore the module to its no-URL state for later tests.
    monkeypatch.delenv("DATABASE_URL", raising=False)
    importlib.reload(base)


def test_env_bool_parses_truthy_values(monkeypatch):
    monkeypatch.setenv("SOME_FLAG", "TRUE")
    assert base.env_bool("SOME_FLAG") is True
    monkeypatch.setenv("SOME_FLAG", "off")
    assert base.env_bool("SOME_FLAG") is False
    monkeypatch.delenv("SOME_FLAG", raising=False)
    assert base.env_bool("SOME_FLAG", default=True) is True


def test_env_list_splits_and_strips(monkeypatch):
    monkeypatch.setenv("SOME_LIST", " a , b ,, c ")
    assert base.env_list("SOME_LIST") == ["a", "b", "c"]


def test_service_metadata_present():
    # The health endpoint depends on these being defined.
    assert settings.SERVICE_NAME == "celpip-backend"
    assert settings.SERVICE_VERSION == "0.1.0"


def test_dev_trusts_only_loopback_vite_origins():
    # The test suite runs under config.settings.dev. Both loopback hostname
    # forms of the Vite dev server must be trusted so proxied auth POSTs clear
    # Django's CSRF origin check — and nothing may be a wildcard.
    trusted = settings.CSRF_TRUSTED_ORIGINS
    assert "http://localhost:5173" in trusted
    assert "http://127.0.0.1:5173" in trusted
    assert all("*" not in origin for origin in trusted)
    # Trust is explicit, not permissive: an arbitrary origin stays untrusted.
    assert "http://evil.example" not in trusted


def test_base_settings_do_not_inject_dev_origins(monkeypatch):
    # Production imports `base` (not `dev`); the loopback trust must not leak in
    # unless explicitly configured via the environment.
    monkeypatch.delenv("CSRF_TRUSTED_ORIGINS", raising=False)
    reloaded = importlib.reload(base)
    assert reloaded.CSRF_TRUSTED_ORIGINS == []


def test_dev_cookie_flags_default_insecure_over_http():
    # Local dev is served over plain HTTP; ``Secure`` cookies would be silently
    # dropped by the browser, breaking the CSRF/refresh/session flow. All three
    # flags must therefore default to False under config.settings.dev.
    assert settings.AUTH_COOKIE_SECURE is False
    assert settings.CSRF_COOKIE_SECURE is False
    assert settings.SESSION_COOKIE_SECURE is False


def test_dev_cookie_flags_respect_explicit_secure_override(monkeypatch):
    # Someone running dev behind TLS can still force secure cookies via the
    # single AUTH_COOKIE_SECURE override, which drives all three flags.
    from config.settings import dev

    monkeypatch.setenv("AUTH_COOKIE_SECURE", "true")
    try:
        reloaded = importlib.reload(dev)
        assert reloaded.AUTH_COOKIE_SECURE is True
        assert reloaded.CSRF_COOKIE_SECURE is True
        assert reloaded.SESSION_COOKIE_SECURE is True
    finally:
        monkeypatch.delenv("AUTH_COOKIE_SECURE", raising=False)
        importlib.reload(dev)


def test_prod_forces_secure_cookies_and_explicit_origins(monkeypatch):
    # Production must never be weakened by an environment override: the cookie
    # flags are forced True and the trusted origins stay exactly what was
    # configured (no wildcard, no injected loopback dev origins). The required
    # production environment must be in place before prod is (re)imported.
    monkeypatch.setenv("SECRET_KEY", "x" * 50)
    monkeypatch.setenv("ALLOWED_HOSTS", "celpip.example")
    monkeypatch.setenv("CSRF_TRUSTED_ORIGINS", "https://celpip.example")
    monkeypatch.setenv("DATABASE_URL", "postgres://u:p@localhost:5432/celpip")
    # A deliberately insecure override must be ignored in production.
    monkeypatch.setenv("AUTH_COOKIE_SECURE", "false")
    try:
        importlib.reload(base)  # pick up the production-like environment
        import config.settings.prod as prod

        reloaded = importlib.reload(prod)
        assert reloaded.AUTH_COOKIE_SECURE is True
        assert reloaded.CSRF_COOKIE_SECURE is True
        assert reloaded.SESSION_COOKIE_SECURE is True
        assert reloaded.CSRF_TRUSTED_ORIGINS == ["https://celpip.example"]
        assert all("*" not in origin for origin in reloaded.CSRF_TRUSTED_ORIGINS)
    finally:
        for var in (
            "SECRET_KEY",
            "ALLOWED_HOSTS",
            "CSRF_TRUSTED_ORIGINS",
            "DATABASE_URL",
            "AUTH_COOKIE_SECURE",
        ):
            monkeypatch.delenv(var, raising=False)
        importlib.reload(base)  # restore the no-URL/no-origin dev state
