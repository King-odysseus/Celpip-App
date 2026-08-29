# Backup & restore runbook

Operational procedures for backing up and restoring the CELPIP backend. All
commands are run from the `backend/` directory with the virtual environment
active. No secrets are stored in this document — substitute real values from
your environment (`.env` / secret manager) at run time.

## What must be backed up

| Asset | Location | Notes |
| --- | --- | --- |
| PostgreSQL database | `DATABASE_URL` | Single source of truth for users, content, attempts, plans. |
| Private media (recordings) | `PRIVATE_MEDIA_ROOT` | Learner speaking audio. Never part of public static/media. |
| Static files (optional) | `STATIC_ROOT` | Rebuildable from source; nice-to-have only. |
| Environment/secret values | secret manager / `.env` | Backed up separately; never committed to git. |

The frontend is rebuilt from source and does not need a database/media backup.

## Backup

### 1. Database (PostgreSQL)

```bash
# Plain SQL dump (portable, human-inspectable).
pg_dump "$DATABASE_URL" --no-owner --no-privileges --clean --if-exists \
  > "backups/celpip-$(date +%Y%m%d-%H%M%S).sql"
```

> On Windows PowerShell use `Get-Date -Format` to build the timestamp, or use a
> fixed name and rotate it. Replace `"$DATABASE_URL"` with the actual
> `postgres://user:password@host:5432/db` value.

For large databases, use the custom format for parallelism and partial restore:

```bash
pg_dump "$DATABASE_URL" --format=custom \
  --file="backups/celpip-$(date +%Y%m%d-%H%M%S).dump"
```

### 2. Private media

```bash
# Tar the recordings directory. Exclude nothing — it is already private.
tar -czf "backups/private_media-$(date +%Y%m%d-%H%M%S).tar.gz" \
  -C "$(dirname "$PRIVATE_MEDIA_ROOT")" "$(basename "$PRIVATE_MEDIA_ROOT")"
```

### 3. Secret values

Export the environment names (never values) into your secret manager or a
separately encrypted store. Do **not** write secret values into a backup file
that sits next to the dump.

## Verify a backup

```bash
# SQL dump is well-formed and non-empty.
test -s "backups/celpip-<timestamp>.sql" && \
  grep -q "CREATE TABLE" "backups/celpip-<timestamp>.sql"

# Custom-format dump lists its contents.
pg_restore --list "backups/celpip-<timestamp>.dump" | head

# Archive lists the recording tree.
tar -tzf "backups/private_media-<timestamp>.tar.gz" | head
```

Automate a weekly restore drill to a scratch database (see below) and confirm
the health endpoint and a seeded content count.

## Restore

> Restore is destructive to the target database. Point at a scratch database
> first, or take a fresh backup before overwriting production.

### 1. Database

```bash
# Stop writes first (maintenance window / read-only mode).
createdb celpip_restore   # or drop & recreate an existing empty target

# Plain SQL restore.
psql "$RESTORE_DATABASE_URL" < "backups/celpip-<timestamp>.sql"

# Custom-format restore (parallel).
pg_restore --dbname="$RESTORE_DATABASE_URL" --jobs=4 --no-owner \
  "backups/celpip-<timestamp>.dump"
```

Then run the migration check (dump should already match the schema, but verify):

```bash
python manage.py migrate --check
```

### 2. Private media

```bash
# Restore into the configured private root.
mkdir -p "$PRIVATE_MEDIA_ROOT"
tar -xzf "backups/private_media-<timestamp>.tar.gz" \
  -C "$(dirname "$PRIVATE_MEDIA_ROOT")"
```

### 3. Verification after restore

```bash
python manage.py check --deploy   # configuration sanity (not a DB check)
python manage.py migrate --check
curl -fsS http://127.0.0.1:8000/api/v1/health/
python manage.py shell -c \
  "from django.contrib.auth import get_user_model; print(get_user_model().objects.count())"
```

Confirm the owner account can sign in, a seeded content set exists, and a
speaking recording replays (private-media path is intact).

## Rollback

| Scenario | Rollback |
| --- | --- |
| Failed database migration during deploy | Re-run the previous deploy's code, or restore the pre-migration dump. |
| Bad release (app code) | Redeploy the previous git tag/commit, then restore the database if the release wrote incompatible data. |
| Accidental data loss | Restore the latest good database + private-media backup into a fresh instance and repoint traffic. |
| Corrupted private media | Restore only the `private_media` archive; the DB references files by key, so both must be consistent with one backup set. |

Keep database and private-media backups from the **same timestamp** so storage
keys in the DB match the files on disk.

## Scheduling

- Database: daily full + point-in-time (WAL archiving) if offered by the host.
- Private media: daily incremental or full, kept in sync with the DB.
- Retention: keep 7 daily, 4 weekly, 12 monthly backups, minimum.
- Test restores: at least monthly.
