#!/bin/sh
# Production entrypoint for the single web service.
#
# Runs database migrations, then hands the process off to Gunicorn. `set -eu`
# aborts on the first error or unset variable so a failed migration never starts
# a half-broken server. Django's static files are already collected in the image
# build and served by WhiteNoise, so no collectstatic runs here.
set -eu

cd /app/backend

# Railway (and any other platform mounting a persistent volume) replaces /data
# at runtime with a fresh root-owned filesystem, which shadows the directory and
# ownership baked into the image. The container therefore starts as root purely
# so this block can hand the mount to the unprivileged runtime user, then
# re-execs itself as that user with gosu — everything below runs unprivileged.
# When the container is already started as a non-root user this is skipped and
# the script behaves exactly as before.
APP_USER=appuser

if [ "$(id -u)" = "0" ]; then
    private_media_root="${PRIVATE_MEDIA_ROOT:-/app/backend/private_media}"
    # Only the mount point itself is chowned, not its contents: it is empty on a
    # first deploy, and later files (speaking recordings, generated renditions)
    # are written by the runtime user already. A recursive chown here would grow
    # slower with every deploy for no benefit.
    mkdir -p "$private_media_root"
    chown "$APP_USER:$APP_USER" "$private_media_root"
    exec gosu "$APP_USER" "$0" "$@"
fi

echo "Running database migrations..."
python manage.py migrate --noinput

# Practice-content bootstrap. Without content the catalog endpoints return an
# empty list and the app shows no questions, so a fresh database (e.g. the first
# deploy against an empty Railway PostgreSQL) must be seeded before it is
# served. `BOOTSTRAP_CONTENT_ON_START` decides when that happens:
#
#   auto (default) — seed only when no published content exists yet, so a fresh
#                    database heals itself and ordinary restarts stay fast and
#                    never touch content.
#   true           — always run the seeds. They are idempotent (each skips items
#                    that already exist), so this only costs startup time.
#   false          — never seed, for a deployment that manages content by hand.
#
# `set -e` makes any seed failure abort startup so a half-seeded database is
# never served.
bootstrap_content="${BOOTSTRAP_CONTENT_ON_START:-true}"

if [ "$bootstrap_content" = "auto" ]; then
    # A failure here (e.g. an unreachable database) aborts startup via `set -e`
    # rather than being mistaken for "content already present".
    published_content_count="$(python manage.py shell --no-imports -c "
from apps.content.models import ContentVersion, PublicationStatus
print(ContentVersion.objects.filter(status=PublicationStatus.PUBLISHED).count())
")"
    if [ "$published_content_count" = "0" ]; then
        echo "No published content found — seeding practice content..."
        bootstrap_content="true"
    else
        echo "Found ${published_content_count} published content versions — skipping seed."
        bootstrap_content="false"
    fi
fi

if [ "$bootstrap_content" = "true" ]; then
    echo "Seeding practice content..."

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

# Natural-voice audio. Seeded Listening audio is locally/OS-synthesized
# development audio; replace it with the configured remote provider (OpenAI by
# default) using LISTENING_TTS_PROVIDER_ORDER / LISTENING_OPENAI_VOICES /
# OPENAI_TTS_MODEL. `--only-local` targets just those assets and leaves any
# remote recordings alone, so this is a no-op once audio is natural. It is
# non-fatal: a transient provider outage must not take the whole app down, so
# failures are logged and the app starts with the existing (working) audio.
#
# A voice/model change never applies to audio that is already natural unless
# forced: set FORCE_REGENERATE_LISTENING_AUDIO=true for exactly one deploy to
# re-synthesize every Listening asset with the current voices/model (e.g. after
# switching the voice pair), then unset it so ordinary restarts stay fast and
# don't re-spend on each restart.
if [ "${FORCE_REGENERATE_LISTENING_AUDIO:-false}" = "true" ]; then
    echo "Force-regenerating listening audio (FORCE_REGENERATE_LISTENING_AUDIO=true)..."
    python manage.py regenerate_listening_audio --force \
        || echo "WARNING: listening audio regeneration had failures; serving existing audio."
else
    echo "Regenerating local-synthesized listening audio (if any)..."
    python manage.py regenerate_listening_audio --only-local \
        || echo "WARNING: listening audio regeneration had failures; serving existing audio."
fi

# AI feedback worker. Speaking and Writing submissions enqueue an AIJob in the
# database; this supervised loop claims and runs them, so learner feedback
# actually lands instead of sitting "queued" forever. It runs in the same
# container as the web process because this deployment is a single service. The
# loop restarts the worker if it ever crashes (e.g. a transient database error)
# and is backgrounded so Gunicorn below can take over as PID 1 via `exec`.
echo "Starting AI feedback worker..."
(
    while true; do
        python manage.py run_ai_worker || true
        sleep 5
    done
) &

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
