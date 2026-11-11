from copy import deepcopy
from types import SimpleNamespace

import pytest
from evidence_fixtures import businesses as businesses
from evidence_fixtures import evidence as evidence
from evidence_fixtures import setup as setup
from sqlalchemy.orm import Session
from test_business import ORIGIN, login

from app.assessments.models import BusinessAssessment
from app.qualification.models import AssessmentEvidence
from app.qualification.provider import MAPPING
from app.qualification.scoring import RULES, evaluate


def sample():
    answers = []
    for qid, spec in MAPPING["questions"].items():
        kind = spec["type"]
        value = "Sample"
        if kind == "Number":
            value = 0
        elif kind == "Polar-Yes/No":
            value = True
        elif kind not in {"Text-Short", "Text-Long"}:
            value = [{"choice_id": qid + "choice", "value": "sample", "label": "Sample"}]
        answers.append(
            dict(
                key=spec["key"],
                question_id=qid,
                question_type=kind,
                question_result_id=qid + "result",
                parent_result_id="parent",
                extraction_version=MAPPING["extraction_version"],
                provenance="surveyvista_self_reported",
                state="answered",
                normalized_value=value,
            )
        )
    return SimpleNamespace(
        answers=answers,
        provider_response_id="parent",
        extraction_version=MAPPING["extraction_version"],
        evidence_kind="self_reported",
    )


def test_complete_deterministic_explainable_and_immutable():
    row = sample()
    before = deepcopy(row.answers)
    a = evaluate([row], None, [])
    assert a == evaluate([row], None, [])
    assert row.answers == before
    assert a["readiness"]["score"] == 73
    assert a["readiness"]["classification"] == "Ready with gaps"
    assert [d["weight"] for d in a["readiness"]["dimensions"]] == [30, 25, 20, 15, 10]
    assert a["completeness"]["percent"] == 100
    assert a["confidence"]["classification"] == "self_reported"
    assert a["confidence"]["independently_verified_claims"] == []
    assert all(d["reasons"] for d in a["readiness"]["dimensions"])


def test_unknown_not_zero_and_age_not_penalized():
    row = sample()
    initial = evaluate([row], None, [])
    row.answers[5]["normalized_value"] = 100
    assert evaluate([row], None, [])["readiness"] == initial["readiness"]
    row.answers = row.answers[:1]
    result = evaluate([row], None, [])
    assert result["readiness"]["score"] == 100
    assert result["completeness"]["percent"] == 10
    empty = evaluate([], None, [])
    assert empty["readiness"]["score"] is None
    assert empty["readiness"]["classification"] is None


@pytest.mark.parametrize(
    "change", ["foreign_parent", "qid", "duplicate", "malformed", "provenance"]
)
def test_invalid_or_disputed_claim_not_scored(change):
    row = sample()
    if change == "foreign_parent":
        row.answers[0]["parent_result_id"] = "foreign"
    elif change == "qid":
        row.answers[0]["question_id"] = "unexpected"
    elif change == "duplicate":
        row.answers.append(deepcopy(row.answers[0]))
    elif change == "malformed":
        row.answers[0]["normalized_value"] = []
    else:
        row.answers[0]["provenance"] = "verified"
    result = evaluate([row], None, [])
    assert result["completeness"]["answered"] == 9
    assert result["confidence"]["classification"] == "conflicting"


def test_conflicting_snapshots_and_profile_and_legacy():
    a, b = sample(), sample()
    b.answers[0]["normalized_value"] = "Different"
    result = evaluate([a, b], None, [])
    assert result == evaluate([b, a], None, [])
    assert result["confidence"]["conflicting_claims"] == ["registered_name"]
    profile = SimpleNamespace(name="Different", country="Sample", sector="Sample", goal="Goal")
    assert evaluate([a], profile, [1])["confidence"]["classification"] == "conflicting"
    assert evaluate([a], profile, [1])["completeness"] == {
        "answered": 10,
        "expected": 10,
        "percent": 100.0,
        "usable_for_scoring": 9,
    }
    a.extraction_version = "legacy"
    assert evaluate([a], None, [])["readiness"]["score"] is None


def test_malformed_legacy_payload_is_safe_and_does_not_mutate():
    row = sample()
    row.answers.extend([None, {"key": []}, {"key": "unexpected"}])
    assert evaluate([row], None, [])["completeness"]["answered"] == 10
    row.answers = {"old": "format"}
    assert evaluate([row], None, [])["readiness"]["score"] is None


@pytest.mark.parametrize(
    "score,label",
    [
        (80, "Highly ready"),
        (79, "Ready with gaps"),
        (60, "Ready with gaps"),
        (59, "Developing"),
        (40, "Developing"),
        (39, "Early readiness"),
    ],
)
def test_versioned_thresholds(score, label):
    config = deepcopy(RULES)
    config.update(declared_score=score, identity_score=score, version="test-v2")
    result = evaluate([sample()], None, [], config)
    assert result["readiness"]["classification"] == label
    assert result["readiness"]["version"] == "test-v2"


def test_api_scoring_is_scoped_readonly_and_cannot_unlock_introductions(
    evidence, setup, businesses
):
    client, url, _, assessment_id = evidence
    assert client.post(url + "/ingest", json={}, headers=ORIGIN).status_code == 201
    before = client.get(url + "/evidence").json()
    path = f"/api/businesses/{businesses[0]}/qualification"
    response = client.get(path)
    assert response.status_code == 200
    body = response.json()
    assert body["readiness"]["version"] == RULES["version"]
    assert body["policy"]["introduction_allowed"] is False
    assert body["policy"]["discovery_eligible"] is True
    assert body["confidence"]["classification"] in {"self_reported", "conflicting"}
    assert client.get(url + "/evidence").json() == before
    other = client.get(f"/api/businesses/{businesses[1]}/qualification").json()
    assert other["readiness"]["score"] is None
    assert other["assessment_evidence"] == []
    with Session(setup[1]) as db:
        original = deepcopy(db.get(AssessmentEvidence, before["id"]).answers)
        db.get(BusinessAssessment, assessment_id).integration_mode = "shared_public_link"
        db.commit()
        assert db.get(AssessmentEvidence, before["id"]).answers == original
    assert client.get(path).json()["readiness"]["score"] is None
    assert login(setup, "bob").get(path).status_code == 403
    client.cookies.clear()
    assert client.get(path).status_code == 401
