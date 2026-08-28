"""Shared pytest fixtures for the backend test suite."""
import pytest
from django.core.cache import cache
from rest_framework.test import APIClient


@pytest.fixture(autouse=True)
def _clear_throttle_cache():
    """Reset the throttle cache between tests so buckets do not leak."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def csrf_client() -> APIClient:
    """A client that enforces CSRF, for testing cookie-mutating endpoints."""
    return APIClient(enforce_csrf_checks=True)
