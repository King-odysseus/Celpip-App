# Production deployment

How to run the backend in production, the required environment values, and the
deployment checks to perform. Development settings (`config.settings.dev`) are
unaffected by these changes.

## Select production settings

```bash
export DJANGO_SETTINGS_MODULE=config.settings.prod
```

`config.settings.prod` imports the shared base and then enforces:

- `DEBUG=False`.
- A strong `SECRET_KEY` (it refuses the development fallback).
- A non-empty `ALLOWED_HOSTS`.
- A non-empty `CSRF_TRUSTED_ORIGINS` (scheme://host of the SPA origin).
- A non-empty `DATABASE_URL` (PostgreSQL; the SQLite fallback is dev-only).
- `SECURE_SSL_REDIRECT`, HSTS, and secure cookies.

It raises `ImproperlyConfigured` at startup if any required value is missing,
so a misconfiguration fails fast rather than serving insecurely.

## Required environment

| Variable | Required | Notes |
| --- | --- | --- |
| `DJANGO_SETTINGS_MODULE` | yes | `config.settings.prod` |
| `SECRET_KEY` | yes | Long random value; never the dev default. |
| `ALLOWED_HOSTS` | yes | Deployed hostname(s), comma-separated. |
| `CSRF_TRUSTED_ORIGINS` | yes | e.g. `https://app.example.com`. |
| `DATABASE_URL` | yes | PostgreSQL URL; SQLite is for development only. |
| `CORS_ALLOWED_ORIGINS` | conditional | Only needed for a separately hosted (cross-origin) frontend. Use the exact SPA origin(s); never `*` with credentials. A same-origin SPA needs none. |
| `PRIVATE_MEDIA_ROOT` | yes | Writable dir **outside** any static/media web root. |
| `OPENAI_API_KEY` | only for live AI | Backend-only; never in `VITE_*` or the browser. |
| `TRUST_PROXY_SSL_HEADER` | conditional | `true` only behind a proxy that strips inbound `X-Forwarded-Proto`. |
| `SECURE_SSL_REDIRECT` | recommended | `true` (default) unless TLS is fully handled at the proxy. |
| `SECURE_HSTS_SECONDS` | recommended | e.g. `31536000`; start lower, then raise. |
| `LOG_FORMAT` | recommended | `json` for structured logs. |

## TLS / proxy setup

1. Terminate TLS at a trusted reverse proxy (nginx/Caddy/load balancer).
2. If the proxy sets `X-Forwarded-Proto`, set `TRUST_PROXY_SSL_HEADER=true` **and**
   configure the proxy to strip any inbound `X-Forwarded-Proto` header first —
   otherwise a client can spoof HTTPS.
3. Either enable `SECURE_SSL_REDIRECT=true` in Django, or enforce the redirect at
   the proxy. Do not enable both redirect + a stale HSTS without testing.

## Static & private media

- Serve `STATIC_ROOT` from the proxy or a CDN (`python manage.py collectstatic`).
- `PRIVATE_MEDIA_ROOT` must be served **only** through the authenticated
  speaking-audio view — never as a public static/media alias.

## Database

- Use PostgreSQL (`DATABASE_URL`). Run `python manage.py migrate` on deploy.
- Keep `private_media` on persistent storage, referenced by storage key.

## Deployment checks

Run these before and after each deploy:

```bash
# No pending model changes, no missing migrations.
python manage.py makemigrations --check --dry-run
python manage.py migrate --check

# System/config sanity; --deploy flags production hazards.
python manage.py check --deploy

# Collect static assets into STATIC_ROOT.
python manage.py collectstatic --noinput --clear
```

After starting the service, verify:

```bash
curl -fsS https://app.example.com/api/v1/health/
# expect {"status":"ok","service":"celpip-backend","version":"0.1.0"}

# Security headers are present.
curl -sSI https://app.example.com/api/v1/health/ | grep -iE \
  "x-frame-options|x-content-type-options|strict-transport-security|x-request-id"
```

Expected headers: `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`,
`Strict-Transport-Security` (once HSTS is active), and an `X-Request-ID` on
every response. Logs must be structured and must never contain response text or
audio contents.

## Runtime operations

- **AI worker**: run `python manage.py run_ai_worker` in a supervised process.
- **Retention**: schedule `python manage.py retention` daily (dry-run) and
  `python manage.py retention --execute` on a separate schedule.
- **Owner account**: `python manage.py bootstrap_owner --identifier owner` once.

See `docs/BACKUP_RESTORE.md` and `docs/RELEASE_CHECKLIST.md`.
