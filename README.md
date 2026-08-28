# CELPIP-General Practice Platform

An original, full-stack practice platform for candidates preparing for the
four-skill **CELPIP-General test used for immigration**.

> **Unofficial.** This application is independent and is not affiliated with,
> endorsed by, or operated by CELPIP or Prometric. "CELPIP" is used only to
> identify the test being prepared for. No official practice content is
> reproduced.

This repository is a monorepo. Architecture is governed by
[`docs/CELPIP_PLATFORM_PLAN.md`](docs/CELPIP_PLATFORM_PLAN.md).

## Current status — Phase 1

Phase 1 adds the smallest end-to-end account slice on top of the Phase 1A shell:

- **Custom user & profile.** A case-insensitive identifier (username *or* email)
  with optional email metadata, Argon2 password hashing, and a one-to-one
  `LearnerProfile` holding exam date, a default target level plus optional
  per-skill targets, daily minutes, preferred weekdays, and timezone.
- **Loose registration.** Exactly one identifier + one password (six-character
  minimum, no confirmation, no mandatory email verification). Registration
  returns a one-time, high-entropy recovery code.
- **SimpleJWT sessions.** A 15-minute access token returned in JSON (held only
  in memory by the SPA) and a rotating 7-day refresh token in an HttpOnly,
  auth-scoped cookie. Old refresh tokens are blacklisted on rotation; logout
  revokes them. All unsafe authentication endpoints are CSRF-protected.
- **Recovery-code reset, throttled auth, generic auth errors**, a `me/profile`
  API, and a `bootstrap_owner` management command.
- **Frontend.** A typed fetch client (access token in memory, `credentials:
  include`, CSRF bootstrap/header, one refresh-and-retry after a 401), an
  `AuthProvider` with refresh-on-load, accessible Register / Sign In / Recovery
  / Account pages, a protected Account route, profile onboarding, and a
  Dashboard with a timezone-aware exam countdown, target, four skill cards, a
  readiness empty state, and a recommended next activity.

Sample Learn/Practice pages and the Dashboard stay viewable without an account;
saving a profile and progress requires the loose account. Later phases add the
practice and mock engines.

## Layout

```text
/
├─ backend/     # Django + DRF project (config/ + apps/ + tests/)
├─ frontend/    # React + Vite + Tailwind SPA
├─ docs/        # Architecture plan and ADRs
├─ .env.example # Names of every environment variable (never values)
└─ README.md
```

## Prerequisites

- Python 3.11+ (developed against 3.13)
- Node.js 20+

## Backend

```bash
cd backend
python -m venv .venv
# Windows:  .venv\Scripts\activate
# POSIX:    source .venv/bin/activate
pip install -e ".[dev]"

# Copy env names and fill values as needed. Without DATABASE_URL the backend
# falls back to a local SQLite file, so no PostgreSQL is required for Phase 1A.
cp ../.env.example .env

python manage.py migrate

# Optional: seed the single owner account. The exam date defaults to
# 2026-10-10 (a command default, not a global constant) and is overridable.
python manage.py bootstrap_owner --identifier owner --password "your-password"
# The recovery code is printed once — store it securely.

python manage.py runserver
```

Verify the health endpoint:

```bash
curl http://127.0.0.1:8000/api/v1/health/
# {"status": "ok", "service": "celpip-backend", "version": "0.1.0"}
```

Run the backend checks:

```bash
pytest
```

### Configuration

All settings are read from the environment (see `.env.example`). Settings are
split into `config.settings.base` (shared) and `config.settings.dev`
(local development). `DJANGO_SETTINGS_MODULE` selects the active module and
defaults to `config.settings.dev`.

- **`DATABASE_URL`** — a database URL (e.g. `postgres://…`). When absent, the
  backend automatically uses a local SQLite file (`backend/db.sqlite3`), which
  is also the default for the test suite. PostgreSQL support is configured and
  ready for later phases.
- **`SECRET_KEY`** — required in production; a development fallback is used
  when unset in dev.
- **`DEBUG`, `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`** — see `.env.example`.
- **Auth cookies / CSRF** — `AUTH_REFRESH_COOKIE_NAME`, `AUTH_COOKIE_PATH`,
  `AUTH_COOKIE_SAMESITE`, `AUTH_COOKIE_SECURE` (defaults to on outside DEBUG),
  and `CSRF_TRUSTED_ORIGINS`. Phase 1 assumes same-origin deployment (the Vite
  dev proxy serves the SPA and API from one origin), so `SameSite=Lax` cookies
  and the double-submit CSRF token are sufficient.
- **Throttling** — `THROTTLE_AUTH_LOGIN`, `THROTTLE_AUTH_REGISTER`,
  `THROTTLE_AUTH_RECOVERY`, `THROTTLE_ANON`, `THROTTLE_USER`.
- **`OWNER_PASSWORD`** — used by `bootstrap_owner` when `--password` is omitted.

## Frontend

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173
```

Quality gates:

```bash
npm run typecheck
npm run test       # Vitest + Testing Library
npm run build
```

The Vite dev server proxies `/api` to the Django backend on
`http://localhost:8000`.

## Design language

The visual system is adapted from the sibling LifeInTheUk application:
midnight navy (`#0B0B45`) primary, warm bronze (`#966238`) accent, raised
cards, pill buttons, monospaced numerals, and light/dark/system themes. It
honours accessibility requirements: visible focus states, reduced-motion
handling, and 44×44px minimum touch targets. No LifeInTheUk product or domain
code is copied — only the design language is adapted.
