# Milestone 2G — native Salesforce / SurveyVista

## Implementation

Server-only `backend/app/salesforce/client.py` uses existing httpx, Salesforce
v68.0, client-credentials OAuth, an application-scoped token cache, bounded
timeouts and one authentication renewal/retry on HTTP 401. No general POST retry
or credentials/payload logging is implemented. Missing expires_in uses a
conservative five-minute local cache; 401 also invalidates/renews the token.
The configured HTTPS My Domain is pinned, including the returned instance origin;
redirects and arbitrary query-continuation hosts are rejected.

New authenticated POST endpoints beneath `/api/businesses/{business}/assessments`:

- `/{assessment}/dispatch`: actual recipient last name/email required. Company
  and country come from the authorized business profile. Creates one Lead with
  `Kobentra_Assessment_Requested__c=true`. The existing native Flow requests email
  invitation delivery; delivery itself is not confirmed by this application.
- `/{assessment}/sync`: reconcile the Lead, then query SurveyVista results through
  standard Salesforce REST/SOQL. Verify Lead, configured survey, Completed status,
  timestamp and response Id before setting completed_verified. Existing list,
  detail, initiate and configuration endpoints remain. Native mode rejects the
  shared-public-link launch endpoint; the UI shows recipient/dispatch and sync
  controls rather than a respondent URL. No respondent-specific URL is fabricated.

The result status/survey field API names were not supplied in the verified
configuration. Runtime Describe discovers a unique Completed picklist field and
survey reference whose target-object keyPrefix matches the verified survey ID.
Ambiguity fails closed. Optional SALESFORCE_RESULT_SURVEY_FIELD and
SALESFORCE_RESULT_STATUS_FIELD select administrator-verified names, which still
must match authoritative metadata. The Lead lookup and completion timestamp use
the exact user-verified field names. No Premium Integration API is used.

## Durable idempotency and reconciliation

The database transaction locks the business, fixes the recipient/payload and a
random correlation UUID, and commits sending BEFORE making the external POST.
Another request/process, a timeout, crash or uncertain local commit cannot issue
a second POST for the same assessment. Only an explicit 401 has one controlled
authentication retry. Later requests return the durable state. Even known remote
failures are conservatively uncertain; there is no automatic resend/reset.

The standard Lead Description stores the exact opaque assessment/correlation
marker. No new Salesforce field is assumed or created. Lost-response recovery
enumerates recent accessible Leads using SOQL with bounded pagination and compares
the exact marker locally (Description is not SOQL-filterable). Company/last name/
email are secondary consistency checks, never the primary association. Zero,
multiple or mismatched candidates never authorize a new invitation. A pinned
Salesforce origin prevents silently reusing associations across orgs.

Read/write tenancy, owner/admin permissions and trusted-Origin JSON CSRF checks
reuse the existing boundaries. Dispatch payload snapshots contain recipient PII
in the backend database only and are not included in API responses. Preserve the
Description marker and provide the integration user appropriate access to the
created Lead. Failed or incomplete bounded scans require operator review.

## Migration and preservation

New revision `2g001` follows `2f001`, adding nullable salesforce_lead_id,
correlation_id, dispatch_state, dispatch_started_at and dispatch_payload. Unique
Lead/correlation constraints and the expanded integration-mode check preserve
legacy rows. Native rows are not rebound from shared-link records. Downgrade
refuses to discard populated native associations. Frozen schema snapshots permit
offline SQLite batch SQL; PostgreSQL offline SQL and local SQLite round-trips pass.
Legacy-row preservation and schema-drift checks pass. No remote migration ran.

## Validation

147 backend tests passed, including mocked OAuth renewal/cache expiry, successful
dispatch, repeated/concurrent requests, ambiguous timeouts, server failure,
zero/duplicate reconciliation candidates, unauthorized tenants, incomplete and
mismatched results, verified completion, and legacy migration preservation.
Scoped Ruff lint/format and Git whitespace checks pass. Frontend lint, typecheck,
8 unit tests and production build pass. No live provider or native email-delivery
test was executed. One existing Starlette/httpx test-tool warning remains.

Files: new salesforce/ client and results modules; assessments/ dispatch,
synchronize and native_routes modules; assessment model/schema/provider/service,
config/main and .env.example updates; revision 2g001; native/migration/client tests
and fixtures; frontend assessments/ NativeAssessment and contract/page formatting
updates. The user's existing .sf metadata-catalog change was left untouched.

## Exact next controlled test

1. Review and explicitly approve applying any unapplied `2f001` prerequisite and
   `2g001` to the intended Neon database. After approval, run from backend:
   `.\.venv\Scripts\python.exe -m alembic upgrade 2g001`.
2. Confirm the existing server-only Salesforce credentials, API/Lead/package read
   permissions and tested Flow are correct. Set SALESFORCE_DISPATCH_ENABLED=true
   in backend/.env for this controlled run; no credential values need be printed.
3. Start the backend on 8002 and frontend on 5173. Sign in to an authorized test
   business, open Assessments, enter one consenting recipient's real last name and
   email, and request exactly one invitation. Inspect the correlated Lead and native
   invitation in Salesforce. Repeating dispatch must not create another Lead.
4. Complete the emailed survey, select Reconcile/check completion, and confirm a
   unique result matches the stored Lead, survey a0Zaj00000JUZOnEAP, Completed
   status and authoritative completion time. If metadata inference is ambiguous,
   verify exact field names through Describe and set the optional overrides;
   never weaken evidence checks or match by email/business name.
5. If dispatch is uncertain and no unique marker can be found, stop for review.
   Do not reset sending/uncertain or manually resend to bypass duplicate protection.

No Flow modification, deployment, commit, push, real Lead creation or production
database migration was performed here. A native invitation and completion remain
unverified end-to-end until this controlled test succeeds.

OAuth reference: https://developer.salesforce.com/blogs/2024/02/invoke-rest-apis-with-the-salesforce-integration-user-and-oauth-client-credentials
