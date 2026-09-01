# CELPIP-General Practice Platform

An original, full-stack practice platform for candidates preparing for the
four-skill **CELPIP-General test used for immigration**.

> **Unofficial.** This application is independent and is not affiliated with,
> endorsed by, or operated by CELPIP or Prometric. "CELPIP" is used only to
> identify the test being prepared for. No official practice content is
> reproduced.

The current bank contains **712 practice activities**: 163 Reading sets, 173
Listening sets, 152 Writing prompts, and 224 Speaking prompts. Reading and
Listening contain 1,325 objective questions in total. Every reviewed source
activity is available as Guided (Foundation), Independent (Developing), and
Challenge stages so support decreases and cognitive demand rises progressively
— except the 8 small full-length-mock filler sets (see Phase 11 below), which
exist only to let a mock section reach its exact official question count and
are single-stage by design.

This repository is a monorepo. Architecture is governed by
[`docs/CELPIP_PLATFORM_PLAN.md`](docs/CELPIP_PLATFORM_PLAN.md).

## Current status — Phase 10B (full Speaking comparison)

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

Phase 2 adds the first complete practice loop:

- A versioned, editorially reviewed bank of eight original Reading sets across
  all four CELPIP-General Reading task families (24 questions, 96 choices).
- Human-only publishing for AI-assisted drafts, immutable published versions,
  provenance, validation tooling, and learner APIs that never expose answer
  keys or explanations early.
- Learn sessions with untimed, immediate evidence-based feedback and Practice
  sessions with a learner-selected timer and corrections held until submission.
- Frozen session content, server-side scoring, revision-aware idempotent
  autosave, private account ownership, and 24-hour guest resume tokens stored
  only in browser session storage. Practice accuracy is never presented as an
  official CELPIP score.
- Responsive email, notice, table, article, and viewpoint readers using the
  LifeInTheUk-inspired design system.

Learn and Practice work without registration. An account remains the easiest
way to keep durable progress as later analytics and study-plan phases arrive.

Phase 3 adds Listening preparation:

- All six current CELPIP-General Listening task families, represented by six
  reviewed original Canadian-context scripts and 18 objective questions.
- Locally generated development recordings using installed Canadian-English
  synthetic voices. They are labelled transparently and are not represented as
  official audio or exact test-centre acoustics.
- Private audio outside public static/media roots, metadata/checksum validation,
  short-lived signed access, byte-range streaming, and session ownership checks.
- Unlimited replay plus post-answer transcript study in Learn mode; one playback
  grant and delayed transcript/corrections in timed Practice mode.

Phase 4 adds Writing preparation:

- Both CELPIP-General Writing tasks — Writing an Email and Responding to Survey
  Questions — with original Canadian-context prompts.
- A timer, plain-text editor, server-computed word count, revision-aware
  idempotent autosave, and an immutable final submission.
- Honest non-official self-review across the four official rubric dimensions;
  no automatic CELPIP score or level is produced.

Phase 5 adds Speaking recording:

- All eight CELPIP-General Speaking task shells with preparation and response
  countdowns.
- Browser `MediaRecorder` capture, private storage, owner/guest-authorized
  replay, and immutable submission.
- Guided self-review only — no transcript, pronunciation score, or level yet.

Phase 6 adds audited AI services:

- A provider-neutral database queue with a deterministic `fake` provider for
  development/tests and a live `openai` adapter behind a backend-only key.
- Structured, versioned writing evaluation and speaking transcription/evaluation
  with immutable, labelled, non-official estimates.
- AI drafting that can only publish through the existing human editorial gate.
  See [`docs/AI_SERVICES.md`](docs/AI_SERVICES.md).

Phase 7 adds adaptive learning:

- A mistake bank that merges repeated errors and drives a review queue.
- Four-skill progress and an explainable readiness summary.
- Versioned study-plan generation that adapts scheduled tasks to recent results.

Phase 8 adds the compact full mock:

- A frozen four-component attempt in the official order — Listening → Reading →
  Writing → Speaking — with server-timed sections and restricted navigation.
- Every current CELPIP-General task family (20 in total), with corrections
  embargoed until the whole mock completes.
- Honest compact scope: the original starter bank has fewer objective questions
  than the live test, so this is a task-family simulation, not an official score
  conversion. Results never convert raw accuracy into an official CELPIP level.

Current format facts and the implementation interpretation are source-dated in
[`docs/CONTENT_RESEARCH_LOG.md`](docs/CONTENT_RESEARCH_LOG.md).

Phase 9 hardens the backend for production and adds the account privacy UI:

- **Privacy-safe account export** at `GET /api/v1/me/export/`: profile,
  attempts, progress, mistakes, study plans, mock summaries, and authored
  response text/metadata — never hashes, tokens, answer keys, other users, or
  private audio.
- **Self-service account deletion** at `DELETE /api/v1/me/` with password or
  recovery-code confirmation, cascading owned data and private recordings.
- **Account privacy UI** in the frontend: a "Download my data" action that
  saves a timestamped UTF-8 JSON export via a Blob/object URL, plus a clearly
  separated danger zone that gates account deletion behind an explicit
  confirmation (password or recovery code) and clears the in-memory session
  before returning to the public dashboard.
- **Retention command** `python manage.py retention` (dry-run by default;
  `--execute` deletes) for expired guest sessions/recordings and stale failed
  AI jobs, with bounded age arguments.
- **Request/correlation IDs** on every response plus structured logging that
  never writes response text or audio.
- **Production settings** (`config.settings.prod`) with enforced secrets,
  TLS/HSTS, and security headers. See [`docs/PRODUCTION_DEPLOYMENT.md`](docs/PRODUCTION_DEPLOYMENT.md),
  [`docs/BACKUP_RESTORE.md`](docs/BACKUP_RESTORE.md), and
  [`docs/RELEASE_CHECKLIST.md`](docs/RELEASE_CHECKLIST.md).

Phase 10 completes the authenticated candidate Dashboard:

- **Dashboard read model** at `GET /api/v1/me/dashboard/`, reusing the progress
  selector for per-skill measures and layering on totals, streak, recent
  results, practice signals, today's tasks, and a transparent readiness
  planning indicator. Selector-only — no schema migration is required.
- **Totals** — total objective questions completed and total completed attempts
  across all four skills.
- **Study streak** — unique submitted/completed activity dates (objective
  submissions, Writing/Speaking submissions, and completed study tasks) in the
  learner's profile timezone. The streak is anchored on today when today has
  activity, otherwise on yesterday; future dates are ignored.
- **Recent results** — the five most recent objective-accuracy and AI-assisted
  estimate outcomes, newest first, with skill, task, date, measure, value, and
  destination but no prompt text or responses.
- **Strongest / needs-attention practice signals.** Cross-skill comparison uses
  an unofficial *practice planning indicator*: objective accuracy stays 0–100
  for Listening/Reading, while the AI-assisted Writing/Speaking midpoint is
  divided by 12 and multiplied by 100. Unpractised skills are shown as
  needs-attention, never silently scored zero, and objective accuracy is never
  labelled an estimated CELPIP level.
- **Overall readiness** is a transparent, deterministic *practice planning
  indicator*, not a CELPIP score or score prediction:

  ```
  0.30 × coverage + 0.25 × recency + 0.25 × volume + 0.20 × performance
  ```

  - **coverage** — share of the four skills with at least one objective result
    or AI-assisted estimate.
  - **recency** — 100 for activity today, minus 10 per full day since the most
    recent activity (floor 0).
  - **volume** — 10 points per completed attempt, capped at 100. A completed
    attempt is a submitted session, counted even when AI feedback is still
    queued or failed.
  - **performance** — average of per-skill practice planning signals.

  Every component's weight, value, and explanation is shown to the learner, and
  the indicator returns an *insufficient-evidence* state (no number) until at
  least one attempt exists. A prominent disclaimer states it is unofficial and
  not a score prediction. Per-skill measures remain separate on the Progress
  page.

The Dashboard is split into cohesive, accessible subcomponents (stats, today's
tasks, skill estimates, practice signals, recent results, readiness) with
loading, error, empty, and anonymous states.

Phase 11 adds a full-length mock (backend; see
[`docs/CELPIP_PLATFORM_PLAN.md`](docs/CELPIP_PLATFORM_PLAN.md#phase-11--full-length-content-and-scoring-ready-assembly)):

- `POST /api/v1/mocks/` accepts `{"scope": "full_length_simulation"}` to
  assemble each Listening/Reading section to the current official question
  count (8/5/6/5/8/6 and 11/8/9/10) from several distinct, published content
  versions, while the default (`compact_task_family_mock`) keeps working
  exactly as before.
- Original filler content
  (`backend/apps/content/mock_full_length_filler_data.py`) closes the gaps a
  4-question-only bank can't reach on its own, so every section hits its exact
  target with no duplicated content in one attempt.
- Some sections legitimately need an extra set beyond the natural 4+4
  pairing; that set is flagged simulated-unscored — indistinguishable during
  the attempt, excluded from raw accuracy after submission, exactly as
  CELPIP describes its own live test.
- No frontend UI yet requests the full-length scope; the mock workspace still
  drives the compact mock by default.

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

# Seed and validate the reviewed original Reading bank. Both commands are safe
# to repeat; seeding never overwrites an existing authored item.
python manage.py seed_reading_content
python manage.py validate_content --published-only

# Listening audio is committed for the starter bank and generated ONCE, then
# reused. On Windows the first local recording comes from the reviewed scripts
# using installed OS voices (this is the final "local" fallback):
# powershell -File ..\scripts\generate-listening-audio.ps1
python manage.py seed_listening_content

# To upgrade to natural voices, regenerate through the provider order
# (openai → azure → local; see LISTENING_TTS_PROVIDER_ORDER in .env.example).
# This is independent of AI_PROVIDER, only replaces a file after strict WAV
# validation, and never destroys a working recording if every provider fails.
# Old stored WAVs stay in use until you run this:
python manage.py regenerate_listening_audio --dry-run          # preview only
python manage.py regenerate_listening_audio --slug apartment-heating-plan --force
python manage.py regenerate_listening_audio --force            # all sets

# Separate per-provider renditions never touch the canonical WAV above; each is
# written to its own private path (listening_renditions/{provider}/{id}.wav).
python manage.py generate_listening_renditions --provider openai --dry-run
python manage.py generate_listening_renditions --provider openai,azure --force
python manage.py generate_listening_renditions --provider openai --slug apartment-heating-plan

# Writing and Speaking banks seed the same way; all seed commands are safe to
# repeat and never overwrite an existing authored item.
python manage.py seed_writing_content
python manage.py seed_speaking_content

# Optional: seed the single owner account. The exam date defaults to
# 2026-10-10 (a command default, not a global constant) and is overridable.
python manage.py bootstrap_owner --identifier owner --password "your-password"
# The recovery code is printed once — store it securely.

python manage.py runserver
```

The compact full mock requires a signed-in account and one published original
prompt for every one of the 20 task families. It is assembled on demand via
`POST /api/v1/mocks/`; `POST /api/v1/mocks/{id}/start/` begins the server-timed
sequence and `GET /api/v1/mocks/{id}/results/` stays embargoed until all four
components finish.

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

- **`DATABASE_URL`** — a database URL. In development, when it is absent, the
  backend automatically falls back to a local SQLite file
  (`backend/db.sqlite3`), which is also the default for the test suite.
  Production (`config.settings.prod`) requires a PostgreSQL `DATABASE_URL`
  (e.g. `postgres://…`) and refuses to start without it (see
  `docs/PRODUCTION_DEPLOYMENT.md`).
- **`SECRET_KEY`** — required in production; a development fallback is used
  when unset in dev.
- **`DEBUG`, `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`** — see `.env.example`.
- **Auth cookies / CSRF** — `AUTH_REFRESH_COOKIE_NAME`, `AUTH_COOKIE_PATH`,
  `AUTH_COOKIE_SAMESITE`, `AUTH_COOKIE_SECURE` (defaults to on outside DEBUG),
  and `CSRF_TRUSTED_ORIGINS`. Phase 1 assumes same-origin deployment (the Vite
  dev proxy serves the SPA and API from one origin), so `SameSite=Lax` cookies
  and the double-submit CSRF token are sufficient. The dev proxy uses
  `changeOrigin`, so Django still sees the browser's loopback `Origin`; the dev
  settings therefore trust `http://localhost:5173` and `http://127.0.0.1:5173`
  for CSRF origin checking (production trusts only the explicit
  `CSRF_TRUSTED_ORIGINS` you configure — never a wildcard).
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
