#!/bin/sh
# Production entrypoint for the single web service.
#
# Runs database migrations, then hands the process off to Gunicorn. `set -eu`
# aborts on the first error or unset variable so a failed migration never starts
# a half-broken server. Django's static files are already collected in the image
# build and served by WhiteNoise, so no collectstatic runs here.
set -eu

cd /app/backend

echo "Running database migrations..."
python manage.py migrate --noinput

PORT="${PORT:-8000}"
WEB_CONCURRENCY="${WEB_CONCURRENCY:-2}"
GUNICORN_TIMEOUT="${GUNICORN_TIMEOUT:-60}"

echo "Starting Gunicorn on 0.0.0.0:${PORT} (workers=${WEB_CONCURRENCY})..."
exec gunicorn config.wsgi:application \
    --bind "0.0.0.0:${PORT}" \
    --workers "${WEB_CONCURRENCY}" \
    --timeout "${GUNICORN_TIMEOUT}" \
    --access-logfile - \
    --error-logfile -
