# Vercel deployment readiness (no deployment performed)

## Topology and project settings

Use two Vercel projects from this repository:

| Project | Root directory | Settings |
| --- | --- | --- |
| Backend | `backend` | FastAPI preset, Python 3.12, `app.main:app`, Fluid compute enabled, 300-second function limit |
| Frontend | `frontend` | Vite preset, `npm ci`, `npm run build`, output `dist` |

The browser uses **one public frontend origin**. Its `/api/*` external rewrite
forwards to the backend, preserving `/api/*`; the next rewrite handles React deep
links while excluding API paths. Replace the reserved `.invalid` backend destination
in `frontend/vercel.json` with the actual stable backend deployment origin before
deploying the frontend. Do not point the rewrite back to the frontend itself.
No domains have been provisioned or assumed by this implementation.

Production frontend requests default to relative `/api` URLs. Explicitly set
`VITE_API_BASE_URL=/` for deployment. Vercel builds reject an explicitly configured
cross-origin/localhost API base. Do not use two unrelated `vercel.app` origins
for direct browser API calls: that makes cookie authentication cross-site. The
proxy retains host-only, HttpOnly, SameSite=Lax cookies on the frontend, including
the OAuth browser-binding cookie. No cookie-domain or SameSite=None workaround is
needed. Verify Set-Cookie/Origin forwarding in the approved HTTPS smoke test.

Disable Vercel deployment protection on the public frontend/backend target used by
the demo, or configure an explicitly supported access path before testing. A Vercel
login challenge is not Kobentra authentication. Do not expose bypass secrets in
browser variables. Use stable domains, not arbitrary preview URLs, for Google OAuth.
Preview environments must use isolated database/configuration and must not inherit
production mutation credentials without authorization.

## Environment variables

Backend required names:

- `APP_ENV` (production), `DATABASE_URL` (Neon PostgreSQL, never SQLite)
- `FRONTEND_URL`, `GOOGLE_REDIRECT_URI`, `CORS_ORIGINS`
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `OAUTH_SESSION_SECRET`
- `SALESFORCE_INSTANCE_URL`, `SALESFORCE_CLIENT_ID`, `SALESFORCE_CLIENT_SECRET`
- `SALESFORCE_DISPATCH_ENABLED`

Optional/existing backend names:

- `PLATFORM_OWNER_GOOGLE_SUBJECT`
- `SALESFORCE_RESULT_SURVEY_FIELD`, `SALESFORCE_RESULT_STATUS_FIELD`
- `SESSION_COOKIE_NAME`, `SESSION_LIFETIME_HOURS`
- `SURVEYVISTA_LAUNCH_URL` (legacy only; not the native invitation workflow)
- `SALESFORCE_BUSINESS_DELETION_ENABLED` (keep disabled)

Vercel provides `VERCEL` automatically. The application refuses Vercel startup in
development/test mode. Public mode rejects SQLite, incomplete Google configuration,
weak OAuth signing secrets, HTTP frontend URLs, cross-origin callbacks and extra
CORS origins. Use a random OAuth signing secret of at least 32 characters.

Frontend: `VITE_API_BASE_URL` only. No provider/database/admin secret belongs in
`VITE_*`. The API proxy destination is a non-secret routing setting in vercel.json,
not an invented environment-substitution feature. CORS_ORIGINS is a JSON array with
exactly the frontend HTTPS origin. FRONTEND_URL is that origin; GOOGLE_REDIRECT_URI
is that same origin followed by `/api/auth/google/callback`.

Local `.env`, SQLite files, virtual environments, tests and backups are excluded
from deployment uploads. Runtime dependencies are constrained by the existing lock
file; no new dependencies were introduced. Both matching and qualification JSON
rules/mapping files are explicitly included in the backend function bundle.

## Neon and schema/data readiness

No database connection, remote migration or data copy was performed. Existing
repository migration head is `2l002`; deployment preparation requires no migration.
Before deployment, separately authorize a read-only Neon revision/data audit. If
the target is behind, approve and apply only the reviewed existing migrations from
a trusted local environment, never from the Vercel build or app startup. Do not run
create_all, reset schemas or use an automatic migration install hook.

Use the Neon **pooled** connection endpoint in DATABASE_URL, URL-encoded credentials,
verified TLS and channel binding. The existing engine supplies a trusted CA bundle.
Production uses NullPool (no retained pool per serverless instance), disables psycopg
prepared statements and bounds connection, SQL and lock waits. Transaction-local SQL
timeouts do not leak across pooled sessions. Real Neon pooler behavior is unverified
in this preparation pass. Place the function close to the Neon region where practical.

The local SQLite two-account demonstration is not automatically present in Neon.
Confirm the two business IDs, native assessment links, ten-answer snapshots and market
preferences exist in the target. If absent, a separately reviewed/authorized transfer
must preserve IDs, relationships, immutable evidence, dispatch correlation/payload
and audit history. Do not upload SQLite, create replacement Leads, resubmit surveys,
match rows by name, or assume business data is replicated. Do not copy active sessions
or pending OAuth transactions as a shortcut. All existing local records remain intact.

## Google and Salesforce

In Google Cloud, configure the web OAuth client with the exact public frontend HTTPS
origin and the proxied frontend callback. Ensure consent/test-user or publication
settings permit the demo accounts. Backend configuration must match exactly. Secure
cookies follow from the enforced HTTPS callback; session and OAuth transactions are
persisted in Neon and survive instance recycling. Do not log callback query strings,
cookies, credentials or request bodies; review platform log retention/access.

Reuse the existing Salesforce My Domain, client-credentials connected/external client
app, integration user, object permissions, Describe access and Lead-triggered Flow.
Confirm any Salesforce login/IP policy permits the Vercel runtime without weakening
security blindly. Do not alter the Flow or package configuration during deployment.
The integration is server-to-server and needs no new browser OAuth callback.
Enable dispatch only after the target DB/configuration review and controlled-test
approval; a live invitation creates a Salesforce Lead and is a write.

## Serverless processing and recovery

Nothing runs after the request as an assumed background worker. Existing visible-tab
polling performs `/sync`, native completion verification and immutable ingestion.
The bounded polling window and Retry processing control remain unchanged. Returning
to the workspace resumes checks; going offline does not continue processing.

Vercel's function limit is configured to 300 seconds, but the frontend's external
rewrite has a separate **120-second** origin timeout. Production Salesforce work
therefore shares a 60-second request budget across authentication, metadata, queries
and retries, with reduced per-phase HTTP timeouts as the budget is consumed. Database
connection timeout is 10 seconds, statement timeout 20 seconds and lock timeout 5
seconds. These are bounded operations, not proof of a strict total wall-clock SLA;
verify real request latency/cold starts. If slow metadata repeatedly exhausts the
budget, stop and diagnose the actual calls rather than raising limits blindly.

Completion commits before import, so import failure cannot undo verified completion.
Durable dispatch claim/correlation, immutable evidence and DB locks remain authoritative
across instances. A killed/ambiguous dispatch must reconcile; never resend/reset it.
Request budgets are context-local, not shared between concurrent invocations. Token
cache is only a per-instance optimization, never durable coordination. API responses
are explicitly non-cacheable at both the application and frontend proxy boundaries.

## Matching audit

Production matching contains no Nigeria/Ghana gate, hardcoded test business IDs or
demo-directory dependency. Membership, suspension, deletion and native-evidence
checks still apply. Reciprocal target-country interest uses normalized declared
country strings; inconsistent aliases need clarification, not invented geographic
equivalence. Industry/capacity/timing mappings are intentionally limited and unknown
choices remain unknown. Tests also cover Senegal/Benin and Togo/Côte d’Ivoire pairs
with isolated synthetic evidence; this does not change SurveyVista choice options.

## Approval-gated deployment sequence

1. Review these local changes and approve deployment/configuration actions separately.
2. Select stable frontend/backend domains. Replace the reserved API rewrite destination.
3. Authorize the Neon schema/data audit; resolve any migration or data-transfer gap
   through separate approved operations. Back up the approved target before writes.
4. Create/configure the two Vercel projects and server-only environment variables.
   Verify `.vercelignore` exclusions; never upload the repository root with local work.
5. Configure Google origins/callback and verify existing Salesforce integration-user
   access. Keep Salesforce deletion disabled. Review preview/production isolation.
6. After explicit approval, deploy backend then frontend. Inspect the actual Linux
   Python build, JSON assets, function duration/region and proxy routing. No live Vercel
   build or bundle-size/runtime verification was executed during preparation.
7. Test HTTPS Google login, restoration, logout, secure cookies, Origin rejection,
   deep links and absence of API caching. Verify an unrelated tenant gets no private data.
8. Reuse existing approved Neon assessments/snapshots to verify readiness, reciprocal
   discovery and snapshot idempotency. A new native invitation requires separate
   permission; verify automatic processing, bounded failure recovery and no duplicate
   Lead only in that controlled run. Preserve introduction restrictions.
9. Confirm no requests target localhost, SQLite or development domains. Record deployment
   URLs and smoke-test evidence before declaring the public application ready.

The existing `/api/health` payload still contains historical Phase 1 integration
labels. Treat it only as liveness, never proof of database/provider connectivity.

Official references: [FastAPI](https://vercel.com/docs/frameworks/backend/fastapi),
[Python](https://vercel.com/docs/functions/runtimes/python),
[function limits](https://vercel.com/docs/functions/limitations),
[rewrites](https://vercel.com/docs/routing/rewrites),
[external proxy timeout](https://vercel.com/docs/errors/router_external_target_error).
