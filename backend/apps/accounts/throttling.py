"""Auth throttles keyed by both client IP and the submitted identifier.

Keying on the identifier as well as the IP slows credential-stuffing against a
single account from rotating IPs, and password-spraying from one IP across many
identifiers, without needing to store the raw identifier in the cache key.
"""
from __future__ import annotations

from rest_framework.throttling import SimpleRateThrottle

from .models import fingerprint_identifier


class _IdentifierScopedThrottle(SimpleRateThrottle):
    """Base throttle whose bucket is (client IP, hashed identifier)."""

    def get_cache_key(self, request, view):  # noqa: ANN001
        identifier = ""
        if isinstance(getattr(request, "data", None), dict):
            identifier = request.data.get("identifier", "") or ""
        ident = f"{self.get_ident(request)}:{fingerprint_identifier(identifier)}"
        return self.cache_format % {"scope": self.scope, "ident": ident}


class _IPScopedThrottle(SimpleRateThrottle):
    """Throttle an endpoint by client IP, independent of submitted data.

    The identifier-scoped bucket is useful for stopping attacks against one
    account, but it must be paired with an IP bucket on public endpoints. An
    attacker should not be able to evade registration limits simply by sending
    a different identifier on every request.
    """

    def get_cache_key(self, request, view):  # noqa: ANN001
        return self.cache_format % {
            "scope": self.scope,
            "ident": self.get_ident(request),
        }


class LoginRateThrottle(_IdentifierScopedThrottle):
    scope = "auth_login"


class RegisterRateThrottle(_IdentifierScopedThrottle):
    scope = "auth_register"


class RecoveryRateThrottle(_IdentifierScopedThrottle):
    scope = "auth_recovery"


class RegisterIPRateThrottle(_IPScopedThrottle):
    scope = "auth_register_ip"


class LoginIPRateThrottle(_IPScopedThrottle):
    scope = "auth_login_ip"


class RecoveryIPRateThrottle(_IPScopedThrottle):
    scope = "auth_recovery_ip"
