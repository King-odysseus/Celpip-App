"""Development settings.

Imports everything from :mod:`config.settings.base` and relaxes a few values
for local work. Still environment-driven: set variables in ``backend/.env`` or
your shell to override any of these.
"""
from __future__ import annotations

from .base import *  # noqa: F401,F403
from .base import env_bool

# Local development is verbose by default, but DEBUG can still be forced off
# via the environment when needed.
DEBUG = env_bool("DEBUG", default=True)

# Convenience hosts for local work, in addition to anything supplied via
# ALLOWED_HOSTS in the environment.
ALLOWED_HOSTS = list({*ALLOWED_HOSTS, "localhost", "127.0.0.1", "[::1]"})  # noqa: F405

# The SPA runs on the Vite dev server and reaches Django through Vite's proxy
# (``changeOrigin: true``), which rewrites the Host to the backend but forwards
# the browser's real ``Origin`` header. Django's CSRF middleware then compares
# that Origin against ``CSRF_TRUSTED_ORIGINS`` for unsafe requests, so the
# loopback Vite origins must be trusted or every auth POST (register/login/
# refresh/recovery) fails origin checking with a 403.
#
# Trust ONLY the two loopback hostname forms of the Vite dev server, merged with
# anything explicitly configured in the environment. This is not a wildcard and
# does not affect production, which imports ``base`` (not this module) and still
# requires an explicit ``CSRF_TRUSTED_ORIGINS``.
DEV_VITE_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]
CSRF_TRUSTED_ORIGINS = [  # noqa: F405
    *CSRF_TRUSTED_ORIGINS,  # noqa: F405
    *[o for o in DEV_VITE_ORIGINS if o not in CSRF_TRUSTED_ORIGINS],  # noqa: F405
]

# Cookie "Secure" flags must be OFF for local HTTP development. ``base`` derives
# them from ``not DEBUG`` while DEBUG is still its base default of ``False`` (dev
# only flips DEBUG to True *after* importing base), so the refresh, CSRF, and
# session cookies come out ``Secure`` and browsers silently drop them over plain
# HTTP — which is exactly why ``GET /api/v1/auth/csrf/`` hands back a cookie the
# browser discards and every subsequent auth POST then fails CSRF. Recompute the
# flags here for HTTP dev: default to insecure, but still honour an explicit
# ``AUTH_COOKIE_SECURE`` override for anyone running dev behind TLS. Production
# imports ``base``/``prod`` (not this module) and keeps its forced-secure values.
AUTH_COOKIE_SECURE = env_bool("AUTH_COOKIE_SECURE", default=False)
CSRF_COOKIE_SECURE = AUTH_COOKIE_SECURE
SESSION_COOKIE_SECURE = AUTH_COOKIE_SECURE
