# Kobentra AI — Phase 1

Current public-deployment preparation: [Vercel deployment guide](docs/VERCEL-DEPLOYMENT.md).
The Phase 1 setup and disconnected-feature descriptions below are historical; see
[Hackathon MVP](docs/HACKATHON-MVP.md) for the current authenticated workflow.

Local review checkpoint for an enterprise-oriented West African business matchmaking platform. Prepared for the user-stated West Africa Dreamin’ 2026 hackathon target, 21 November 2026. This repository contains a preview and tested foundation, not a production service.

## Run locally (PowerShell)

Frontend, terminal 1:
```powershell
Set-Location D:\kobentra-ai\frontend
npm ci --cache D:\kobentra-ai\work\npm-cache
npm run dev -- --port 5173 --strictPort
```
Open http://127.0.0.1:5173. Sign-up and sign-in validate locally and explicitly report that authentication is unavailable. `/onboarding` configures a fictional demo profile. `/demo` can also be opened directly without signing in; it is never a real authenticated workspace.

Backend, terminal 2:
```powershell
Set-Location D:\kobentra-ai\backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --cache-dir D:\kobentra-ai\work\pip-cache -r requirements-lock.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
```
Health: http://127.0.0.1:8000/api/health. Backend startup does not connect to a database. `/api/workspace` always requires authentication and rejects fabricated identity headers/tokens. Browser preview does not call this API.

No `.env` is needed for the safe defaults. Optional examples exist in each app folder. Do not put secrets in `VITE_*` variables. Keep servers bound to loopback.

## Database configuration — Phase 2A

SQLite remains the default. Settings load `DATABASE_URL` from `backend/.env` regardless of the process working directory; environment variables override that file. No credentials are required for local development. Copy `backend/.env.example` only when no `.env` already exists, and keep it ignored by Git.

PostgreSQL URLs using `postgresql://` or `postgresql+psycopg://` use the existing psycopg 3 dependency. The former is normalized to the latter. URL-encode special characters in usernames/passwords. PostgreSQL requires a host, database, username and password. TLS defaults to `sslmode=verify-full&channel_binding=require`; weaker or ambiguous options are rejected. Allowed query options are sslmode, channel_binding, sslrootcert and connect_timeout; service/host overrides and unknown options are rejected. A trusted root certificate file can be provided with sslrootcert if required by the approved environment; do not weaken TLS to address trust failures.

Settings redact the database URL in representations and JSON, and validation messages hide rejected input. Engines disable SQL echo and hide bound parameters. Never print `.env`, a revealed secret URL, raw validation `.errors()` input, DBAPI connection arguments or connection exception payloads. Engine construction is lazy and does not establish a connection; SQLite PRAGMA hooks are registered only for SQLite engines. The API health route remains independent of database availability and does not connect during startup.

**Neon is prepared for configuration only. No Neon connection or remote migration is authorized or performed.** All PostgreSQL tests use placeholder URLs, mocked connections or offline SQL generation. No live PostgreSQL/Neon runtime, RLS, concurrency or migration behavior has been verified.

```powershell
Set-Location D:\kobentra-ai\backend
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m alembic check
```
Run these commands only while DATABASE_URL selects local SQLite. Alembic online commands connect to the configured database, so do not run them with a Neon URL until separately approved. With the default configuration they use local `kobentra-local.db`. The initial local migration was already applied during verification. Tests exercise upgrade/downgrade/re-upgrade on a disposable temporary SQLite file, with foreign keys enabled. Do not set up or connect a remote database without new approval.

## Verification

```powershell
Set-Location D:\kobentra-ai\frontend
npm run lint
npm run typecheck
npm test
npm run build
npm audit
# Vite must be running; uses already-installed Microsoft Edge in headless mode.
npm run test:browser

Set-Location D:\kobentra-ai\backend
.\.venv\Scripts\ruff.exe check app tests
.\.venv\Scripts\ruff.exe format --check app tests migrations
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m alembic check
```
Read `docs/PHASE-1-REVIEW.md` for evidence and limitations. Browser JSON and review screenshots are in `work/`, ignored as generated local material. TypeScript 5.9 is intentionally within the installed lint parser's supported range. The explicit minimatch 11 override remediates the glob amplification advisory in development tooling; lint/build/tests are checked with this override. Inter is bundled locally with its upstream license in the installed package; no remote font requests.

## Project structure

- `frontend/src/components/`: shared image, CTA and eyebrow components.
- `frontend/src/features/public/`: editorial public pages.
- `frontend/src/features/auth/`: honest local auth validation and onboarding.
- `frontend/src/features/demo/`: fictional data and interactive local workspace.
- `frontend/src/features/contracts.ts`: typed frontend/provider contracts.
- `backend/app/`: configuration, models, authorization helpers, schemas, errors and disconnected integration contracts.
- `backend/migrations/`: initial schema migration and dialect-aware environment.
- `backend/tests/`: authorization, schema, configuration and migration tests.

## Demo retention and boundaries

All sample businesses and the sample event are fictional. Profile details persist only in sessionStorage under `kobentra-demo-profile`. Theme uses localStorage under `kobentra-theme`. Requests, pipeline stages and event saves remain in React memory and reset on page reload or exit. Settings clears the demo profile and in-memory demo records. Nothing is sent, no contact information is disclosed and no external outcome is represented as real. Do not enter real passwords, personal information or private business details.

Email signup, Google OAuth, real profiles/discovery, AI matching, notifications, two-party introduction acceptance, private contact release, cross-tenant publication and durable pipelines are unimplemented. Salesforce and EventSpark are disconnected; adapter methods explicitly raise rather than fake success. No credentials or OAuth tokens exist in this project.

No commit, push, deployment, Salesforce connection, EventSpark installation, OAuth configuration or remote database operation was performed during Phase 2A.
