# Release checklist

Steps to run before tagging and deploying a release. Backend commands run from
`backend/` with the virtual environment active; frontend commands run from
`frontend/`. No secret values appear here.

## Pre-release (local)

- [ ] `git status` is clean and the release branch is up to date.
- [ ] `pytest` passes (full suite, including the new export/deletion/retention
      and settings tests).
- [ ] `ruff check apps config tests` reports no issues.
- [ ] `python manage.py makemigrations --check --dry-run` reports "No changes".
- [ ] `python manage.py migrate --check` succeeds.
- [ ] `python manage.py check` (and, for prod, `python manage.py check --deploy`)
      reports no errors.
- [ ] Frontend changes pass the full frontend suite (`npm run typecheck`,
      `npm run test`, and `npm run build`).
- [ ] Account export/deletion UI is smoke-tested and accessible: "Download my
      data" produces a JSON file; deletion requires password/recovery-code
      confirmation, cascades owned data, and clears the in-memory session;
      keyboard and screen-reader checks pass on both flows.
- [ ] `docs/CELPIP_PLATFORM_PLAN.md` status line reflects the implemented phase.

## Privacy / security review

- [ ] Account export returns only the learner's own data: no password/recovery
      hashes, tokens, answer keys, other users, or private audio binaries.
- [ ] Account deletion requires a password or recovery-code confirmation and
      cascades owned sessions, plans, mistakes, mocks, and private recordings.
- [ ] Retention command defaults to dry-run; `--execute` is explicit and its
      age arguments are bounded.
- [ ] Request IDs are on every response and structured logs never contain
      response text or audio.
- [ ] `SECRET_KEY`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `DATABASE_URL`
      (PostgreSQL), and TLS/HSTS are configured per
      `docs/PRODUCTION_DEPLOYMENT.md`.

## Release

- [ ] Tag the commit: `git tag -a v0.1.0 -m "Phase 9 production hardening"`.
- [ ] Back up the database and private media (see `docs/BACKUP_RESTORE.md`).
- [ ] Deploy migrations first (`python manage.py migrate`), then code.

## Post-deploy verification

- [ ] `curl -fsS https://app.example.com/api/v1/health/` returns `ok`.
- [ ] Security headers present (`X-Frame-Options`, `X-Content-Type-Options`,
      `Strict-Transport-Security`, `X-Request-ID`).
- [ ] A smoke login/export/delete round-trip succeeds on a test account.
- [ ] `python manage.py retention` (dry-run) reports expected counts without
      deleting anything.
- [ ] Logs are structured and contain no response bodies or audio.

## Rollback

- Redeploy the previous git tag; restore the pre-release database + private
  media if the release wrote incompatible data. See `docs/BACKUP_RESTORE.md`.
