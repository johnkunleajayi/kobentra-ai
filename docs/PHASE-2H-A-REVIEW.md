# 2H-A — response evidence foundation

Baseline HEAD: `49aae2b`. Existing 2G Salesforce client, dispatch, reconciliation
and Flow behavior are unchanged. The pre-existing .sf metadata-catalog change was
preserved. No blocker was found during scoped read-only Salesforce inspection.

## Verified source mapping

The verified Lead/survey resolved to Survey Result `a0Vaj00000gXv8zEAC`.
A direct Question Result query using that exact parent returned ten unique rows;
every row's parent link matched. Question metadata confirmed survey membership,
stable question IDs, definitions and types. `qualification/mapping.json` pins
those IDs/types and plaintext-definition SHA-256 hashes under `surveyvista-v1`.
Runtime extraction never maps claims using HTML text or positional order alone.

Text-short/long use Answer_Text; years use Answer_Number; choice answers use the
Question Result Choice junction plus Answer Choice metadata. Q4/Q5 are Multiple
Choice. Q8 is Polar-Yes/No with documented-in-org True/False values and Yes/No
choice labels. Answer_Text and Answer_Value are retained independently; they are
not interchangeable. Raw display/selected ordering is retained, not used as identity.
The live sample selected one choice for each multi-select question; synthetic
two-selection tests cover normalization without submitting another live survey.

## Local implementation

New backend `app/qualification/` modules separate provider reads, ID mapping,
normalization, persistence, policy and routes. The exact bound parent is re-read
and checked against Lead, survey, Completed status and the stored completion time
before its children are fetched. The pinned Salesforce org is also checked.
Only completed_verified salesforce_flow assessments qualify. No synchronization
or completion status is changed by ingestion.

Snapshots retain parent/question/question-result/choice IDs, raw values and
selections, normalized values, extraction version, provenance and a content hash.
All claims are self_reported. Missing/unanswered items become explicit gaps;
duplicate, unexpected, malformed, foreign-parent or changed-metadata responses
are rejected atomically. A same-version retry returns the same snapshot; changed
source content produces a conflict and preserves the original. Tenant locks and
database uniqueness handle concurrency.

New revision `2h001` after `2g001` creates assessment_evidence and a composite
assessment/organization uniqueness target for its tenant-safe foreign key. Local
SQLite round-trips, schema drift checking and PostgreSQL/SQLite offline SQL pass.
No remote migration ran. No frontend source or new dependencies were needed.

Authenticated APIs:

- POST `/api/businesses/{business}/assessments/{assessment}/ingest` with `{}`:
  owner/admin, existing trusted-Origin JSON CSRF policy, 201 new / 200 identical.
- GET `/api/businesses/{business}/assessments/{assessment}/evidence`:
  member-scoped private evidence; no-store responses.
- GET `/api/businesses/{business}/qualification`: profile, preferences and
  assessment-source summaries, disclosed gaps and provisional policy.

Discovery eligibility is provisional and does not publish records. The server-side
introduction guard requires independent business_identity verification; survey
completion, business profile and preferences never satisfy it. Independent/supporting
evidence ingestion is future work. Future real introduction routes must call this
guard. No real introduction endpoint, final score or matching algorithm was added.

## Validation and next step

164 backend tests pass, including immutable/idempotent ingestion, concurrency,
typed multi-select/polar handling, bad input/metadata, missing answers, cross-tenant
API/foreign-key rejection, legacy/incomplete rejection and qualification policy.
Scoped Ruff lint/format, frontend lint/typecheck, 8 frontend unit tests and build
pass. One existing Starlette/httpx deprecation warning remains.

Read-only live dry-run of the actual provider/extractor returned ten normalized
answers with zero gaps, all self-reported. Only IDs, counts, metadata and value
types were output; no respondent answers or secrets were logged or saved locally.
Sanitized structural reports are in work/2h-schema-inspection.json and
work/2h-readonly-validation.json. There were no Salesforce or Neon data writes.

Next: review and approve applying `2h001` to the intended Neon database, then use
an authorized business session to POST ingest for its existing verified assessment
and retrieve the snapshot. That persistence check is not yet live-verified.
Source changes require review and a new approved extraction version, never silent
overwrite. No commit, push, deployment or remote schema change was performed.
