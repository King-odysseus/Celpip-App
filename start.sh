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

# Optional one-time practice-content bootstrap for a fresh database (e.g. the
# first deploy against an empty Railway PostgreSQL). Disabled by default so
# ordinary restarts never touch content. Every seed is idempotent — it skips
# items that already exist — so re-running is safe, but the guard keeps startup
# fast once content is present. `set -e` makes any seed failure abort startup so
# a half-seeded database is never served.
if [ "${BOOTSTRAP_CONTENT_ON_START:-false}" = "true" ]; then
    echo "BOOTSTRAP_CONTENT_ON_START=true — seeding practice content..."

    # Listening sets require their audio in PRIVATE_MEDIA_ROOT: the seed reads
    # each WAV to record duration/checksum, and the app streams the same files
    # at runtime. That directory is a persistent volume that starts empty, so
    # stage the WAVs bundled in the image into it without ever overwriting a
    # file already present (renditions or regenerated audio stay untouched).
    bundled_listening_audio="/app/backend/private_media/listening"
    listening_audio_dest="${PRIVATE_MEDIA_ROOT:-/app/backend/private_media}/listening"
    if [ -d "$bundled_listening_audio" ]; then
        mkdir -p "$listening_audio_dest"
        for src in "$bundled_listening_audio"/*.wav; do
            [ -e "$src" ] || continue
            dest="$listening_audio_dest/$(basename "$src")"
            [ -e "$dest" ] || cp "$src" "$dest"
        done
    fi

    python manage.py seed_reading_content
    python manage.py seed_listening_content
    python manage.py seed_writing_content
    python manage.py seed_speaking_content
    echo "Practice-content bootstrap complete."
fi

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
