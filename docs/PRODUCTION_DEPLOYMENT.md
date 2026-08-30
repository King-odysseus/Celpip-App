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
| `BOOTSTRAP_CONTENT_ON_START` | optional | `auto` (default) seeds practice content only when the database has none; see below. |

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

### Seeding practice content on a fresh database (Railway)

A brand-new Railway PostgreSQL database has no practice content, and with no
content every catalog endpoint returns an empty list — the app loads but shows
no questions. The entrypoint (`start.sh`) seeds the database for you, controlled
by `BOOTSTRAP_CONTENT_ON_START`:

- **`auto` (default, and what unset means):** after migrations the entrypoint
  counts published content versions. If the count is zero it seeds; otherwise it
  logs the count and starts Gunicorn immediately. A fresh database therefore
  heals itself on the first deploy with no variable to remember, and later
  restarts cost nothing.
- **`true`:** always seed, even when content is present. The seeds are
  idempotent, so this only costs a few seconds per start.
- **`false`:** never seed — for a deployment whose content is managed by hand.

When seeding runs, the entrypoint first stages the Listening audio bundled in
the image into `PRIVATE_MEDIA_ROOT/listening/` (never overwriting existing
files), then runs `seed_reading_content`, `seed_listening_content`,
`seed_writing_content`, and `seed_speaking_content`. All four are idempotent —
they skip content that already exists — and any failure aborts startup so a
half-seeded database is never served.

To confirm a deploy seeded correctly, watch the logs for `Practice-content
bootstrap complete.` before the Gunicorn line, then check the catalog:

```
curl -fsS https://<app>/api/v1/content/reading/
```

A `"count"` of `0` means the database is still empty.

Notes:

- The Listening WAVs live on the persistent `PRIVATE_MEDIA_ROOT` volume after the
  first bootstrap and are reused on every restart; the app also streams them from
  there at runtime.
- To seed manually instead of on start, run the same commands in a one-off shell:
  `python manage.py seed_reading_content` (and the other three).

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

- **AI worker**: `python manage.py run_ai_worker` claims and runs queued AI
  feedback jobs. In this single-service deployment it is started automatically
  by `start.sh` (backgrounded, with a crash-restart loop) alongside Gunicorn.
- **Retention**: schedule `python manage.py retention` daily (dry-run) and
  `python manage.py retention --execute` on a separate schedule.
- **Owner account**: `python manage.py bootstrap_owner --identifier owner` once.

See `docs/BACKUP_RESTORE.md` and `docs/RELEASE_CHECKLIST.md`.
