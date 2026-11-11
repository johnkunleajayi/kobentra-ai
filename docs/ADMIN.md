# Platform administration — 2L-A

For 2L-B business mutations, current administrative states and required migration,
see [ADMIN-MANAGEMENT.md](ADMIN-MANAGEMENT.md). This document describes the original
read-only milestone; current business management is owner-authorized and audited.

Owner-only read endpoints: `GET /api/admin/dashboard`, `/api/admin/users`,
`/api/admin/businesses`, `/api/admin/businesses/{business_id}`. Listings accept
`q` (max 100 characters), `page` (1–100000), `page_size` (1–100; default 20).
Search is literal, case-insensitive; wildcard characters are escaped. Stable ID
ordering and batched membership/owner queries avoid per-row database requests.
Admin and authenticated capability responses are `Cache-Control: no-store`.

## Secure provisioning

Set `PLATFORM_OWNER_GOOGLE_SUBJECT` in backend/.env or the backend secret manager to
the exact Google `sub` already stored on the intended user's verified account as
`users.provider_subject`. Obtain it through a trusted operator-only database/identity
administration channel. Do not match by email, put it in source code, publish it,
or send it to the browser. Unset configuration denies all administrative access.
No live identity was read or provisioned during implementation.

Authorization resolves the existing server-side cookie session and rereads the
stored subject on each administrative request. A central authorization helper can
be extended to additional administrators later; no extra administrators are enabled
in this milestone. Normal tenant endpoints and membership rules remain unchanged.
`/api/auth/me` supplies only a backend-computed `capabilities.platform_admin` boolean;
the existing frontend session request controls navigation without another auth call.

## Data limits

Existing users and organizations/profiles have no creation timestamp columns.
Dates are null / “Not recorded”, never inferred from sessions or assessments.
Business verification/suspension status is not modeled: shown as “not recorded”.
No migration was introduced. Workspace count is organization count; businesses count
profiles. Assessment statuses are aggregated; qualification summary counts self-reported
snapshots, not verified businesses. Business detail reuses qualification evaluation
with eligible evidence, returning summary scores/confidence/gaps only. No raw answers,
tokens, provider response identifiers or recipient contacts are returned. Assessment
history is limited to the most recent 100 records. There are no write actions.

## Local validation / browser steps

```powershell
Set-Location D:\kobentra-ai\backend
.\.venv\Scripts\python.exe -m pytest tests/test_admin.py tests/test_auth_sessions.py tests/test_google_identity.py -q --basetemp=D:/kobentra-ai/work/pytest-2la
.\.venv\Scripts\python.exe -m ruff check app/admin tests/test_admin.py app/config.py app/main.py app/auth_routes.py
Set-Location D:\kobentra-ai\frontend
npm test
npm run lint
npm run build
npx playwright test --config playwright.admin.config.ts
```

For a real local browser session, provision the owner subject securely, then run:

```powershell
Set-Location D:\kobentra-ai\backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8002 --no-access-log
# Separate terminal:
Set-Location D:\kobentra-ai\frontend
npm run dev
```

Sign in normally with the configured Google account. Administration appears in
navigation (inside the mobile menu). Open `/admin`, inspect dashboard, search users
and businesses, paginate and open a business detail. Confirm read-only controls and
unavailable dates. Ordinary accounts must see no Administration entry and get HTTP
403 for admin APIs; signed-out requests get 401. Do not copy cookies or tokens.
Browser automated tests use fictional mocked API responses; backend tests use isolated
SQLite fixtures. No remote database access, migration or Salesforce change is required.
