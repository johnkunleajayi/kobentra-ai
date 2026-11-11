# Business management — 2L-B

## API and independent states

Owner-authorized `POST /api/admin/businesses/{id}/decisions` accepts `action`
(`approve`, `reject`, `verify_identity`, `revoke_identity`, `suspend`, `reactivate`),
`reason`, UUID `request_id`, integer `expected_version`, and `evidence_references`.
Identity verification requires 1–10 nonempty evidence references. These reference
independently reviewed records; this milestone does not authenticate documents.
`PUT /api/admin/businesses/{id}/profile` takes the same reason/request/version and
`profile: {name, sector, country, goal}` using existing onboarding length limits.
`GET /api/admin/businesses/{id}/history?page=1` returns 20 decisions per page.
Actor identity is always server-derived. Mutations require the existing approved
Origin and JSON CSRF checks, existing session and configured platform-owner identity.

States are independent: approval pending/approved/rejected; identity unverified/verified;
access active/suspended. Same-state actions fail with 409. Approval may move between
approved and rejected; verification and access actions must toggle their own state.
Every successful decision increments the version; stale edits fail with 409.
Identical request-ID retries replay the recorded result; changed payloads fail.
Organization row locks serialize decisions with tenant writes. A state change and its
audit insert commit together. Audit records include actor/time/reason/evidence refs and
previous/new values; there is no update/delete audit service, and ORM update/delete is
rejected. Direct database administrators remain responsible for DB-level access control.

## Enforcement and legacy data

Missing state rows mean **pending, unverified, active**. Existing businesses are not
silently approved. Discovery candidates must be approved, active AND explicitly on
the existing publication allowlist. Approval/reactivation never adds allowlist IDs.
Rejected requesters cannot discover; pending active requesters may search but are not
published. Suspended businesses cannot use normal tenant endpoints or writes,
including onboarding retries and assessment initiation. Account business summaries
remain visible so a user can identify their workspace. Platform-owner admin inspection
continues to work. Suspension is business-scoped; it does not suspend the user's account
or prevent registering a distinct business. Previously dispatched Salesforce invitations
are not canceled or modified by suspension.

Owner identity decisions are separate from SurveyVista self-report claims. Qualification
discloses the owner identity decision without upgrading private answer confidence.
Even verified businesses cannot introduce: the mutual-consent introduction workflow
is still unavailable. Readiness rules and matching rules/evidence snapshots are unchanged;
computed compatibility may naturally change after a profile edit.

Changing name/country resets approval to pending and identity to unverified in the same
audited edit. Other supported fields are sector and goal; no additional description
column exists. Local organization name is updated with profile name. Existing Salesforce
dispatch copies name to Lead.Company and country to Lead.Country at initial creation.
Existing Leads, dispatch payloads and SurveyVista results are NOT updated. Sector/goal
are not currently dispatched. Updating Salesforce requires a separately supported,
approved workflow; reconciliation keeps using the original immutable dispatch payload.

## Migration and verification

Migration `2l001` follows `2h001`, adding `business_administration` and
`administrative_decisions`. Upgrade preserves all profiles and evidence. Apply before
running this code against an existing database. **No remote migration has been run.**
SQLite roundtrip/drift and PostgreSQL offline DDL validation are local tests; live
PostgreSQL locking behavior remains unverified.

```powershell
Set-Location D:\kobentra-ai\backend
.\.venv\Scripts\python.exe -m pytest tests/test_admin_mutations.py tests/test_admin_enforcement.py tests/test_admin_migration.py tests/test_admin.py tests/test_matching.py tests/test_qualification_policy.py tests/test_qualification_scoring.py tests/test_discovery_demo.py tests/test_migration.py -q --basetemp=D:/kobentra-ai/work/pytest-2lb
.\.venv\Scripts\python.exe -m ruff check app/admin tests/test_admin_mutations.py tests/test_admin_enforcement.py
Set-Location D:\kobentra-ai\frontend
npm test
npm run lint
npm run typecheck
npm run build
npx playwright test --config playwright.admin.config.ts
```

For manual checks after migration approval, select an isolated SQLite database, migrate
it locally with `python -m alembic upgrade head`, configure the existing platform-owner
Google subject securely and start backend port 8002/frontend 5173 as in ADMIN.md.
Open `/admin/businesses`, inspect badges, then a business. Exercise each decision with
a reason; verification also needs an evidence reference. Confirm history, stale-version
rejection, profile edits and cancellation. Suspend a fictional business and verify
normal workspace/assessment/discovery denial while admin inspection still works.
No live administrative mutation has been performed during this milestone.

The 2J demo command still creates only pending fictional businesses. Its publication
flag is not business approval: the platform owner must separately approve the fictional
candidate through these controls before a persistent demo can appear in discovery.
Tests use approved isolated fixtures, never Neon/Salesforce records.
