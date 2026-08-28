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

# During development, allow the browser to talk to the API from any local
# origin only when explicitly requested; otherwise the base allow-list applies.
