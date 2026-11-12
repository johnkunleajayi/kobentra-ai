# Assessment-driven hackathon MVP

No schema migration, automatic approval or identity-verification decision is required.
Historical administrative decisions and audit records remain unchanged. Suspension
and pending deletion still block operations and remove businesses from discovery.
`MATCHING_DISCOVERY_BUSINESS_IDS` is deprecated and ignored by discovery; an empty
setting no longer disables the directory.

## Processing

The authenticated, origin-protected assessment `/sync` endpoint first performs the
existing native completion reconciliation and commits verified completion. It then
imports answers through the existing pinned question mapping and immutable evidence
service. Temporary Salesforce retrieval failures receive at most two attempts per
request; failure never rolls back verified completion. Conflicting source data is
reported for review, never overwritten. Existing matching snapshots are reused;
concurrent imports use existing tenant write serialization and uniqueness constraints.
Neither synchronization nor polling sends an invitation or creates a Lead. Legacy
shared-link assessments retain their original behavior and cannot qualify as native
evidence.

While an owner/admin has a visible business workspace open, the browser checks up
to three most recent dispatched/native-completed assessments every eight seconds,
for at most forty cycles. It uses existing cookie authentication and write-origin
CSRF protection. Successful imports refresh assessment history and discovery.
Discovery also refreshes every fifteen seconds while visible so an independently
completed partner can appear without a restart. The retry control restarts bounded
checks; it never resends invitations. Checks pause in hidden tabs. **There is no
offline/background worker**: return to the workspace or press Retry processing
after the polling window expires. Responses requiring source-data review pause
until an explicit retry. Read-only members cannot initiate processing writes.

## Discovery and scoring

Every request evaluates current database records. Eligibility requires an active,
non-deleting business with market preferences and ten valid, nonconflicting answers
from verified native evidence, with exact survey/result/version/provenance linkage.
Missing or legacy evidence cannot be substituted by administrative approval.
The directory discloses only business ID, name, sector, country and derived
compatibility explanations, never contacts, raw answers or a partner's readiness.

`kobentra-matching-v1`, revision `assessment-mvp-1`, retains weights 30/25/20/15/10
and minimum coverage 60% across three dimensions. Intent recognizes explicit
supplier/manufacturer and distributor/reseller complements. Reciprocal country
preferences establish market interest, not proof of delivery coverage. Shared food
relevance and complementary food/wholesale/distribution roles provide explainable
industry fit; unknown product scope receives partial coverage or remains unknown.
Comparable explicitly mapped capacity and overlapping readiness windows receive
partial coverage. Unmapped choices remain unknown. A score of 100 is possible on
known compatible dimensions and is **not** 100% evidence coverage or verified trust.

Readiness remains separate, provisional and self-reported. Business age and previous
cross-border experience never gate discovery. Experience may still inform the
readiness rubric. The independent-identity and first-cross-border-engagement gaps
are removed from MVP readiness/discovery requirements. Actual identity records are
unchanged. Separate introduction verification and consent safeguards remain enforced;
this milestone does not enable introductions or certify partnerships.

## Local verification

Use the existing two-account test database without recreating it. In PowerShell:

```powershell
Set-Location D:\kobentra-ai\backend
$env:DATABASE_URL = 'sqlite+pysqlite:///D:/kobentra-ai/work/partner-discovery/e2e-two-accounts.db'
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8002 --no-access-log
```

In another terminal:

```powershell
Set-Location D:\kobentra-ai\frontend
npm run dev -- --port 5173
```

Stop existing development processes with Ctrl+C before restarting. Keep existing
backend OAuth/Salesforce configuration; do not copy secrets into browser code.
Sign into each independent account and open its business workspace → Partner
discovery. Existing ingested assessments are reused; do not request another invitation
or resubmit the two completed assessments. Confirm reciprocal partner cards, score,
coverage and explanations. New user journeys use market preferences → Assessments;
keep the workspace open after submitting the native questionnaire.

The old local fictional demo preparation command creates profiles/preferences only;
it cannot fabricate SurveyVista evidence and no longer qualifies these profiles for
automatic discovery. Automated tests instead use isolated, explicitly fictional
evidence fixtures and mocked providers. Never run demo preparation against Neon.

## Changed files

- Backend `app/assessments/`: `processing.py` (new), `native_routes.py`, `schemas.py`.
- Backend `app/qualification/`: `evidence.py` (new), `policy.py`, `scoring.py`, `service.py`.
- Backend `app/matching/`: `features.py`, `signals.py` (new), `engine.py`, `repository.py`, `routes.py`, `rules.json`, `service.py`.
- Backend `app/admin/eligibility.py`, `app/config.py`.
- Backend `tests/`: `test_mvp.py` (new), `test_admin_enforcement.py`, `test_discovery_demo.py`, `test_matching.py`, `test_qualification_policy.py`, `test_qualification_scoring.py`.
- Frontend `src/features/assessments/`: `AutomaticProcessing.tsx` (new), `AssessmentsPage.tsx`, `NativeAssessment.tsx`, `api.ts`.
- Frontend `src/features/discovery/`: `DiscoveryPage.tsx`, `PartnerCard.tsx`, `types.ts`.
- Frontend `src/features/workspace/`: `BusinessWorkspace.tsx`, `useResource.ts`; `src/features/admin/BusinessManagement.tsx`.
- Frontend `browser-tests/`: `discovery.spec.ts`, `admin.spec.ts`, `deletion.spec.ts`.
- Documentation: this file (new), `MATCHING.md`, `DISCOVERY.md`.

The pre-existing `.sf` metadata modification is unrelated and was not edited.
