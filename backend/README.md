# CELPIP backend

Django + DRF backend for the CELPIP-General practice platform. See the root
[`README.md`](../README.md) for setup and the architecture plan in
[`docs/CELPIP_PLATFORM_PLAN.md`](../docs/CELPIP_PLATFORM_PLAN.md).

Configured entirely through environment variables (see `../.env.example`).
Without `DATABASE_URL` it falls back to a local SQLite database.

## API surface (Phase 1)

- `GET  /api/v1/health/` — liveness probe.
- `GET  /api/v1/auth/csrf/` — set the CSRF cookie.
- `POST /api/v1/auth/register/` — one identifier + password; returns an access
  token, sets the refresh cookie, and returns a one-time recovery code.
- `POST /api/v1/auth/login/` · `POST /api/v1/auth/refresh/` ·
  `POST /api/v1/auth/logout/` — authenticate, rotate, revoke. All unsafe auth
  endpoints require the CSRF token; refresh/logout also act on the cookie.
- `POST /api/v1/auth/recovery-code/reset/` — reset a password with a recovery
  code; returns a fresh code.
- `GET  /api/v1/me/` · `GET/PATCH /api/v1/me/profile/` — current user and
  learner profile.

Views stay thin: request/response shaping lives in
`apps/accounts/{serializers,views}.py`, and all state changes live in
`apps/accounts/services.py` and `apps/accounts/tokens.py`.

## Owner bootstrap

```bash
python manage.py bootstrap_owner --identifier owner --password "…"
# --exam-date defaults to 2026-10-10 (a command default, overridable), and the
# recovery code is printed once.
```
