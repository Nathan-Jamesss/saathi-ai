# Auth, Roles & Dashboard — Design Spec

Date: 2026-09-20
Status: Approved, in implementation

## Context

Saathi.AI currently has zero persistence: no database, no auth, no user
concept. Session state (grade/subject/history) lives only in browser
`localStorage` (`frontend/js/session.js`) and is lost per-device/per-browser.
The backend (`backend/main.py`) is a stateless FastAPI app with CORS wide
open (`allow_origins="*"`, `allow_credentials=False`).

This spec adds two roles — **teacher** and **admin** — real login, a
per-teacher dashboard with persistent session history, and an admin view for
managing teacher accounts and usage. It does **not** cover syllabus
tracking, timetable allocation, or "what to study next" — that is a
separate phase 2 spec, deferred because it's a distinct subsystem (NCERT
syllabus data model, pacing logic, recommendation engine) that should hang
off this account layer once it exists, not be designed blind alongside it.

## Goals

- Teachers can self-signup and log in; admin accounts are seeded, not
  publicly signupable.
- Every `/api/process` call from a logged-in teacher is saved as durable
  history, replacing localStorage as the source of truth.
- Teacher dashboard: view/resume past sessions.
- Admin dashboard: list teachers, activate/deactivate, see usage counts.
- `app.html` requires a valid session; `display.html` does not (same-browser
  `BroadcastChannel` pairing only, per existing `frontend/js/broadcast.js`).
- No password-reset-via-email flow in v1 (admin can reset manually later).

## Non-goals

- Syllabus/NCERT tracking, timetable allocation, AI "next topic" suggestion
  — phase 2.
- Email verification, forgot-password flow.
- Multi-admin management (single seeded admin is enough for v1).
- Changing the existing `/api/tts`, `/api/export` content pipeline logic.

## Architecture

New `backend/auth/` module:

- `models.py` — SQLModel tables: `User`, `SessionHistory`.
- `security.py` — bcrypt password hashing, JWT sign/verify (HS256).
- `deps.py` — FastAPI `Depends`: `get_current_user`, `require_teacher`,
  `require_admin`.
- `routes.py` — `/api/auth/*` endpoints.

Postgres via `DATABASE_URL` env var. `backend/migrations/` via Alembic.

### Data model

```
User
  id              int, PK
  email           str, unique, indexed
  password_hash   str
  role            enum: teacher | admin
  name            str
  school          str, nullable
  grade_default   int
  subject_default str
  is_active       bool, default true
  created_at      datetime

SessionHistory
  id           int, PK
  user_id      int, FK -> User.id
  intent       str
  topic        str, nullable
  grade        int
  subject      str
  language     str
  content_json json
  rating       int, default 0
  created_at   datetime
```

`SessionHistory` is written on every authenticated `/api/process` call,
alongside (not instead of — keep it working offline/logged-out) the
existing localStorage history.

### Auth flow

- `POST /api/auth/signup` — body `{email, password, name, school?,
  grade_default?, subject_default?}`. Role is always forced to `teacher`
  server-side regardless of payload. Returns JWT.
- `POST /api/auth/login` — body `{email, password}`. Returns
  `{token, role, name}`. Rejects if `is_active == false`.
- `GET /api/auth/me` — bearer token required. Returns user profile.
- `GET /api/auth/me/history` — bearer token required. Returns that user's
  `SessionHistory`, newest first.
- `POST /api/auth/admin/teachers` — admin only. Create a teacher account
  directly (covers the "admin creates teachers" half of signup).
- `GET /api/auth/admin/teachers` — admin only. List all teachers with
  `is_active` and a session count.
- `PATCH /api/auth/admin/teachers/{id}` — admin only. Toggle `is_active`.

JWT: 24h expiry, `HS256`, secret from `JWT_SECRET` env var. Frontend stores
token in `localStorage` (`saathi-token`), sends
`Authorization: Bearer <token>` on every API call. `core/keys.py`-style env
lookup pattern reused for `JWT_SECRET`.

Admin bootstrap: `backend/scripts/create_admin.py`, run once manually
(`python -m scripts.create_admin`), reads `ADMIN_EMAIL` / `ADMIN_PASSWORD`
from env, inserts the row. Not exposed via any API route.

### Existing endpoint changes

`/api/process`, `/api/export` gain an optional-auth dependency: if a valid
bearer token is present, the call is attributed to that user and logged to
`SessionHistory`; if absent, behavior is unchanged (works logged-out, same
as today, for backward compatibility / quick demo access). `app.html`
itself enforces "must be logged in" client-side by redirecting to
`login.html` if no token is found — the backend stays permissive so a bare
`curl` demo still works.

### Frontend changes

New pages, existing CSS/JS conventions (vanilla JS modules, no framework):

- `login.html` + `js/auth.js` (`login()`, `signup()`, `logout()`,
  `getToken()`, `authFetch()` wrapper). Redirects: teacher → `dashboard.html`,
  admin → `admin.html`.
- `signup.html` — teacher self-signup form.
- `dashboard.html` — session history list (calls
  `GET /api/auth/me/history`), "resume" loads that entry's context into a
  new session, "Launch classroom" button → `app.html`.
- `admin.html` — teacher table (name, email, active toggle, session count),
  add-teacher form.
- `app.html` — add a guard at top of `js/app.js` init: no token → redirect
  to `login.html`.
- `display.html` — unchanged.
- `index.html` — landing/pitch page unchanged in content, CTA links updated
  to point at `login.html`/`signup.html` instead of `app.html`.

### Deployment

New Render env vars: `DATABASE_URL`, `JWT_SECRET`, `ADMIN_EMAIL`,
`ADMIN_PASSWORD`. Alembic migration (`alembic upgrade head`) added as a
Render pre-deploy/build step. `requirements.txt` gains `sqlmodel`,
`alembic`, `psycopg[binary]`, `pyjwt`, `passlib[bcrypt]`. CORS config
unchanged (`allow_origins="*"`, `allow_credentials=False`) — bearer tokens
don't need cookie credentials.

### Testing

- Backend pytest: signup creates teacher role (ignores forged
  `role: admin` in payload); login rejects wrong password; login rejects
  deactivated user; `require_admin` dependency 403s a teacher token;
  `/api/process` with a valid token writes a `SessionHistory` row.
- Manual smoke test: signup → login → generate a concept explanation →
  confirm it appears in `dashboard.html` history → log in as seeded admin
  → confirm the teacher and their session count appear in `admin.html`.

## Open questions / risks

- Render free Postgres has a 90-day expiry on some free tiers — flag at
  deploy time, pick whichever provider (Render/Neon/Supabase) has the least
  friction when we actually provision it.
- `/api/process` optional-auth (logged-out still works) is a deliberate
  compromise to not break the existing judge-facing demo flow; revisit if
  full lockdown is wanted later.
