# Phase 2D — Real business onboarding

Implemented against branch `main`, starting commit `21cad50`. The existing untracked
`.business-onboarding-backup-20261108-215840/` folder was preserved. No existing
working-tree implementation was overwritten.

## Backend

`app/business/` separates schemas, repository queries, service transactions and HTTP
routes. It reuses the existing `ProfileInput` bounds (100/100/80/500 characters),
whitespace trimming, forbidden extra fields, `require_principal` session dependency
and `get_db` request session.

- `POST /api/businesses`: creates an organization, business profile and owner
  membership in one transaction. Returns the business with status 201. An exact
  normalized replay by the same owner returns the existing business with status 200.
- `GET /api/businesses`: returns `{ "businesses": [...] }`, joined through the
  authenticated user's valid memberships, including each membership role.

Ownership is always server-derived. Unknown identity/ownership fields are rejected.
The write endpoint requires an explicitly trusted Origin and JSON content type,
matching the existing cookie-auth logout CSRF policy. Session cookies remain
HttpOnly; no client authentication or OAuth implementation was replaced.

Registration locks the creator's User row using PostgreSQL `FOR UPDATE` before
checking for an identical owned registration. The existing engine's default
READ COMMITTED isolation allows a waiting request to see the prior commit.
SQLite tests use `BEGIN IMMEDIATE`. Distinct profiles remain allowed for the same
user; there is no one-business-per-user constraint. Transient database failures
roll back and return the application's sanitized error envelope; safe retries
do not leave partial organizations. No request payloads or database exceptions
are logged by this feature. Successful responses use Cache-Control: no-store.

Existing Organization, Membership and BusinessProfile tables are reused. Local
Alembic history confirms head `2c002`; no migration or model change is needed.

## Frontend

`features/business/` contains typed API calls, onboarding, business summaries and
the account business list. `/business/onboarding` uses the restored session and
offers the existing Google login flow when signed out. The form validates required
trimmed values and lengths, prevents repeat in-flight submissions, retains values
on errors and navigates to `/account` after a successful API response.

The account page retrieves memberships' businesses from the backend, including
after reload, and exposes registration/additional-registration actions. It has
loading, empty, retry and error states. Existing form/card styles and themes are
reused. No real profile data is placed in sessionStorage/localStorage.
`/onboarding` and `/demo` remain fictional and independent.

## Validation and limits

Results: 95 backend pytest tests passed, including 18 new business tests and the
existing authentication/identity/session tests. Ruff lint and format checks pass
for the new business package and tests. Frontend ESLint, TypeScript, all 5 unit
tests and production build pass. All 4 focused Playwright tests pass (signed-out
entry, API submission/account reload, failure recovery and demo separation).
The mobile onboarding/account screenshots in `work/` were visually inspected.
Git whitespace checking passes. One existing Starlette/httpx deprecation warning
remains; no dependencies were changed to address this unrelated tooling warning.

Automated backend tests use temporary local SQLite databases and actual opaque
session cookies. They do not connect to production Neon or Google. Browser tests
intercept auth/business responses: they prove frontend behavior, not live database
persistence. SQLite concurrency tests do not prove PostgreSQL lock behavior under
live load. A signed-in manual Neon registration/reload check remains to be done by
the user against the existing configured environment. No live data was created
during implementation, and no Neon schema operations were executed.

No dependencies, authentication flow, public design, Salesforce or ISV integration
were introduced. No commit, push or deployment was performed.

## Manual check (PowerShell, two terminals)

Use the existing configured backend/.env and frontend/.env; do not print secrets.

```powershell
Set-Location D:\kobentra-ai\backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8002 --no-access-log
```

```powershell
Set-Location D:\kobentra-ai\frontend
npm run dev -- --port 5173 --strictPort
```

Open http://127.0.0.1:5173/account, use the existing Google sign-in, choose
Register your business, complete the four fields, and submit. Confirm the account
shows the saved business, then refresh to verify retrieval. Repeat the same form
to verify replay behavior, or change the profile to register another business.
Sign out and verify business data is unavailable; a different account must see
only its own memberships' businesses. Registering here intentionally persists
real records to the configured Neon database. Do not use this manual workflow as
an automated test fixture or reset existing data.

Offline test commands:

```powershell
Set-Location D:\kobentra-ai\backend
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\ruff.exe check app/business tests/test_business.py
Set-Location D:\kobentra-ai\frontend
npm run lint
npm run typecheck
npm test
npm run build
# With the frontend dev server running; requests are mocked, not sent to Neon.
npm run test:browser -- business.spec.ts
```
