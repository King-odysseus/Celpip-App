# syntax=docker/dockerfile:1

# ─────────────────────────────────────────────────────────────────────────────
# Stage 1 — build the Vite single-page app.
# The SPA talks to the backend on the same origin, so the API base URL is a
# root-relative path baked in at build time.
# ─────────────────────────────────────────────────────────────────────────────
FROM node:20-slim AS frontend
WORKDIR /app/frontend

# Same-origin API. Overridable at build time but defaults to the deployed path.
ARG VITE_API_BASE_URL=/api/v1
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

# Install dependencies against the lockfile first for layer caching.
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

# Build the production bundle into frontend/dist.
COPY frontend/ ./
RUN npm run build


# ─────────────────────────────────────────────────────────────────────────────
# Stage 2 — Python backend + built SPA, served by Gunicorn.
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.13-slim AS runtime

# - Fail fast, unbuffered logs, no .pyc files.
# - Production settings module by default (overridable via the environment).
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DJANGO_SETTINGS_MODULE=config.settings.prod \
    SPA_ROOT=/app/backend/spa \
    PRIVATE_MEDIA_ROOT=/data/private_media

WORKDIR /app/backend

# Install the backend and its production dependencies from pyproject. Copying
# the manifest first keeps the (slow) dependency layer cached across code edits.
COPY backend/pyproject.toml backend/README.md ./
RUN pip install .

# gosu drops from root to the runtime user in the entrypoint without leaving
# an intermediate process between the init system and Gunicorn, so signals
# and exit codes still propagate correctly.
RUN apt-get update \
    && apt-get install -y --no-install-recommends gosu \
    && rm -rf /var/lib/apt/lists/* \
    && gosu nobody true

# Application source.
COPY backend/ ./

# Built SPA from the frontend stage — Django/WhiteNoise serve it same-origin.
COPY --from=frontend /app/frontend/dist ./spa

# Start script (LF line endings enforced via .gitattributes).
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Collect Django's own static assets (admin, DRF) for WhiteNoise. Build-time
# placeholders satisfy the strict production settings checks without baking any
# real secrets into the image; runtime values come from the Railway environment.
RUN SECRET_KEY=build-time-placeholder-key-not-used-at-runtime \
    ALLOWED_HOSTS=build.invalid \
    CSRF_TRUSTED_ORIGINS=https://build.invalid \
    DATABASE_URL=postgres://build:build@localhost:5432/build \
    python manage.py collectstatic --noinput

# Non-root runtime user. The ownership set here covers the image's own files
# only: at runtime a mounted volume replaces /data with a root-owned
# filesystem, so this chown of /data does not survive. start.sh fixes the
# mount's ownership as root and then drops to this user with gosu, which is
# why no USER directive follows.
RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /data/private_media \
    && chown -R appuser:appuser /app /data

EXPOSE 8000

CMD ["/app/start.sh"]
