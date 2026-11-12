# Secure business deletion — Recycle Bin policy

Salesforce Leads move to the recoverable Salesforce Recycle Bin through the existing
REST DELETE client. No permanent Salesforce purge or SOAP API is used. Kobentra-owned
local data is removed only after exact remote deletion verification, or when no Lead
is linked. User accounts, immutable audits and an anonymized organization remain.

## API and safeguards

All endpoints require the configured platform owner/session. POSTs enforce JSON and
the approved Origin. Base: `/api/admin/businesses/{id}/deletion`.

- GET `/preview`: name, version, dependency counts, exact Lead/org, implications, token.
- POST base: exact `business_name`, required `reason`, UUID `request_id`,
  `expected_version`, `preview_token`.
- GET base: durable operation and latest 50 immutable transition events.
- POST `/retry`: `{ "operation_id": "<uuid>" }`, scoped to this business.

Targets/actor are server-derived. Confirmation recomputes the preview under the org
lock. Stale previews/versions and conflicting idempotency keys return 409. Retries
reuse the frozen target. Unsettled dispatches, multiple Lead links, converted/merged
Leads, unreviewed schema dependencies and cascading child records block deletion.
`SALESFORCE_BUSINESS_DELETION_ENABLED` remains false by default. Enable only after
explicit live-test approval and org-specific automation/permission review.

## Durable state transitions and recovery

1. Commit operation, `delete_requested` audit and suspended access before any DELETE.
   Normal operations and unrelated administrative mutations remain blocked.
2. No Lead: `local_pending` → transactional local cleanup → `completed`.
3. Linked Lead: `salesforce_pending` → exact org/Lead/correlation validation → REST
   DELETE → verify `IsDeleted=true` → durably commit `local_pending` and an audit event.
4. A separate transaction revalidates the exact recycled Lead immediately before
   controlled local cleanup, tombstone anonymization and atomic `completed` commit.
5. Remote errors, permissions, missing records and uncertain outcomes retain local
   data and record `salesforce_retry`. Retrieve status and resume the original ID.
6. Local failures roll back cleanup but retain the remote checkpoint (`local_pending`).
   Retry rechecks the exact record; an already-recycled Lead receives no second DELETE.

Legacy `awaiting_permanent_purge` operations take the same revalidation path, not a
trusted shortcut. The obsolete state remains in the existing constraint/history only;
new operations never enter it. No migration beyond existing `2l002` is necessary.
No remote migrations were executed.

`salesforce_outcome` is `not_linked`, `not_verified`, or `recycled_verified`.
Completion additionally requires `local_data_removed=true` and `completed_at`.
An error/HTTP timeout never implies successful completion. Do not change frozen IDs,
use replacement keys, or manually mark operations complete.

## Salesforce proof and limitations

The target is the assessment's explicit `salesforce_lead_id` from its settled native
dispatch. The stored origin must match the client, and an Organization query must
match the frozen org ID. Exact-ID `queryAll` must match the original opaque correlation
marker/dispatch digest and deletion state. Names/email are never used to search.
Missing/invisible/404 Leads never establish deletion. Already-deleted Leads require
the same exact identity proof. Lead Describe must permit deletion with complete
cascade metadata and no observed cascade children. Triggers/flows/managed-package
side effects require org-specific review before enabling live deletion.

No cross-system atomicity is claimed. An external restore after committed local
cleanup cannot restore Kobentra data and requires operator review. A restore observed
before local cleanup blocks that cleanup. Salesforce retention/backups are separate.

Official contracts:
- https://developer.salesforce.com/docs/platform/api-rest/guide/dome-delete-record.html
- https://developer.salesforce.com/docs/platform/api-rest/guide/resources-queryall.html

## Local cleanup and retained history

Org-scoped order: evidence, match explanations, introductions, opportunities, events,
preferences, assessments, memberships, profile, administrative state. Unknown models
fail closed. Other tenants, users and sessions remain untouched. An organization named
`Deleted business` preserves audit foreign keys and is excluded from active workspace
counts. Operation data retains IDs/digest, actor, reason and timestamps, not raw answers
or dispatch contacts. Prior immutable admin audits can contain profile edits/reasons;
this is not complete personal-data erasure.

## Local validation

```powershell
Set-Location D:\kobentra-ai\backend
.\.venv\Scripts\python.exe -m pytest tests/test_business_deletion.py tests/test_deletion_salesforce.py tests/test_deletion_migration.py tests/test_migration.py tests/test_admin_mutations.py tests/test_admin_enforcement.py tests/test_salesforce_client.py -q --tb=short --basetemp=D:/kobentra-ai/work/pytest-2lc-recycle
.\.venv\Scripts\python.exe -m ruff check app/admin/deletion tests/test_deletion_salesforce.py
Set-Location D:\kobentra-ai\frontend
npm test
npm run lint
npm run typecheck
npm run build
npx playwright test --config playwright.admin.config.ts
```

Tests use mocked Salesforce and disposable SQLite. For a separately approved manual
test, initialize an isolated local DB and use the normal platform-owner session.
Review the Delete business preview, type its exact name/reason, inspect operation
events and verify other businesses/audits remain. Do not enable live Salesforce
deletion or run remote migrations during this implementation milestone.
