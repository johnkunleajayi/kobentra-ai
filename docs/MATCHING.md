# Matching v1

Authenticated `GET /api/businesses/{business_id}/matches` requires membership in
the requesting organization. It is read-only, returns `Cache-Control: no-store`,
and never initiates introductions. Readiness is not part of compatibility.

`backend/app/matching/rules.json` defines `kobentra-matching-v1`: intent 30%,
industry/capabilities 25%, geography 20%, operations 15%, timing 10%.

- Intent: explicitly configured buyer/supplier or distributor/manufacturer seeking
  pairs, with interests scoped to each other's country, are compatible. This is
  complementary *intent*, never proof of an ability to fulfil it. Other terms are unknown.
- Industry: exact normalized industry agreement is compatible for half the
  dimension (12.5 points of coverage). Capabilities remain unknown; different
  industries are unknown, not necessarily incompatible. No free-text goal parsing.
- Geography: reciprocal target-country interest is compatible; two nonempty target
  lists lacking reciprocity are incompatible **under this rule**, not proof that
  trade is impossible. Missing lists are unknown. Base country is not delivery coverage.
- Operations and timing: unknown. Existing opportunity title/stage and private
  survey claims do not establish pair-specific capacity or timing requirements.
- Conflicting requester identity/country evidence suppresses scoring; conflicting
  industry evidence suppresses the industry dimension. Candidate private assessment
  conflicts cannot be assessed because candidate assessments are never read.

Compatible=100, incompatible=0, unknown=null. At least 60% known weight and three
known dimensions are required for an overall score. Known weights are renormalized;
coverage is returned separately. A score of 100 at 62.5% coverage is *not* a complete
compatibility judgment. Results are provisional and sorted by score then stable ID.

## Explicit discovery disclosure

There is no existing publication/consent field. Registration must not silently
publish all tenant records. The server-side `MATCHING_DISCOVERY_BUSINESS_IDS` JSON
UUID allowlist defaults to `[]` and is bounded to 200 businesses. Configure it only
after obtaining publication approval covering name, sector, country and compatibility
derived from target-country/partner-type preferences. No publication UI is added.
Removing an ID immediately removes it from subsequent requests. Source businesses
need not be published to search. Same-country candidates and the source are excluded.

Returned partner fields are strictly business ID/name/sector/country. Raw preferences,
goals, contacts, opportunities, assessment answers, evidence IDs, readiness scores
and candidate qualification/conflict details are not returned. Candidate private
assessment tables are not queried. Requesters receive their own qualification gaps.
Current discovery policy permits provisional discovery; independent identity
verification remains missing and introductions remain blocked for every candidate.

Existing opportunity, match-explanation and introduction tables cannot represent
a discovery publication or recipient pairing. They are left unchanged; computed
matches are not persisted. No migration, external calls or Salesforce changes.

## Local verification

From `D:\kobentra-ai\backend`:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_matching.py -q
.\.venv\Scripts\python.exe -m ruff check app/matching tests/test_matching.py
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8002 --no-access-log
```

After approval, configure only consented existing business UUIDs in backend/.env as
`MATCHING_DISCOVERY_BUSINESS_IDS=["<approved-business-uuid>"]`. Sign in normally and
GET the matches route for a business you belong to using the existing cookie session.
An empty directory yields an empty list with `directory_status: not_configured`.
Tests use fictional isolated SQLite fixtures only; they do not create live businesses.
