# Hybrid qualification v1

`GET /api/businesses/{business_id}/qualification` adds `readiness`, `completeness`,
`confidence`, `qualification_gaps` and `recommendations`. Existing fields, including
the legacy null `score`, remain compatible. Consumers use `readiness.score`.

Rules live in `backend/app/qualification/scoring.json`, version
`kobentra-readiness-v1`. Change the version whenever the rubric changes. Initial
dimension weights are 30/25/20/15/10; questions share their dimension weight equally.
Known question weights are renormalized; missing, malformed and conflicting claims
are unknown, never zero. No evidence gives a null score/classification. Completeness
and scored weight must accompany scores: a sparse assessment may have a high score.

This deliberately conservative first rubric assigns 70 for a valid preparedness
declaration, 100 for supplied identity fields (completeness only), and 60 for an
explicit absence of cross-border experience. Company age, industry, number of markets,
capacity choice, timeline choice and text length receive no comparative ranking.
Zero years is valid. These are product policy points, not empirically validated
quality/risk measures. Country and industry have no inherent quality ranking.
Validated choice-specific rubrics can replace these points in a later rules version.

Only pinned normalized question identities from completed native assessments with
matching survey/result linkage contribute. Multiple supported snapshots are compared;
disputed fields are excluded rather than silently selecting a convenient response.
Explicit registered-name disagreement with the current profile is disclosed.
Profile completeness and missing market targets produce separate actionable gaps;
target markets are not interpreted as markets already served.

All current sources are self-reported. Consistency never upgrades confidence.
The response vocabulary reserves partially supported and verified-for-specified-claims
for a future authoritative supporting-evidence source; neither is emitted today.
Conflicting is emitted for disputed/malformed claim provenance or identity. No
documents, verification workflow, matching algorithm or independent claims are invented.
Independent business-identity verification remains mandatory before introductions,
regardless of readiness. Provisional discovery remains permitted with disclosed gaps.

Evaluation does not write snapshots or scores. No migration is needed.
