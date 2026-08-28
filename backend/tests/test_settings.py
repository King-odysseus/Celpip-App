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
