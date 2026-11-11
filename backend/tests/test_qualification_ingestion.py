from concurrent.futures import ThreadPoolExecutor

import pytest
from evidence_fixtures import businesses as businesses
from evidence_fixtures import evidence as evidence
from evidence_fixtures import setup as setup
from sqlalchemy.orm import Session
from test_business import ORIGIN, login

from app.qualification.provider import P
from app.qualification.service import ingest
from app.security import Principal


def test_idempotent_typed_evidence_and_self_reported_provenance(evidence):
    client, url, source, _ = evidence
    result = client.post(url + "/ingest", json={}, headers=ORIGIN)
    assert result.status_code == 201
    body = result.json()
    assert body["evidence_kind"] == "self_reported" and len(body["answers"]) == 10
    answers = {a["key"]: a for a in body["answers"]}
    assert len(answers["partnership_types"]["normalized_value"]) == 2
    assert answers["years_operating"]["normalized_value"] == 4
    assert answers["cross_border_experience"]["normalized_value"] is True
    country = answers["primary_country"]
    assert country["raw_value"][P + "Answer_Text__c"] != country["raw_value"][P + "Answer_Value__c"]
    assert country["normalized_value"][0]["value"] == "stored-1-0"
    assert client.post(url + "/ingest", json={}, headers=ORIGIN).json()["id"] == body["id"]
    assert client.get(url + "/evidence").json()["id"] == body["id"]
    assert any("WHERE ArdiraSurvey__Survey_Result__c =" in q for q in source.queries)


def test_source_changes_do_not_overwrite_existing_snapshot(evidence):
    client, url, source, _ = evidence
    old = client.post(url + "/ingest", json={}, headers=ORIGIN).json()
    source.rows[0][P + "Answer_Text__c"] = "Different sample claim"
    assert client.post(url + "/ingest", json={}, headers=ORIGIN).status_code == 409
    assert client.get(url + "/evidence").json()["answers"] == old["answers"]


@pytest.mark.parametrize(
    "case",
    [
        "duplicate",
        "unexpected",
        "malformed",
        "foreign_parent",
        "foreign_choice",
        "metadata_change",
        "bad_order",
    ],
)
def test_unsafe_responses_fail_without_evidence(evidence, case):
    client, url, source, _ = evidence
    if case == "duplicate":
        source.rows[1][P + "Question__c"] = source.rows[0][P + "Question__c"]
    elif case == "unexpected":
        source.rows[0][P + "Question__c"] = "a0Q000000009999AAA"
    elif case == "malformed":
        source.rows[5][P + "Answer_Number__c"] = "not a number"
    elif case == "foreign_parent":
        source.rows[0][P + "Survey_Result__c"] = "a0V000000009999AAA"
    elif case == "foreign_choice":
        source.links[0][P + "Ans_Choice__c"] = source.links[-1][P + "Ans_Choice__c"]
    elif case == "metadata_change":
        source.questions[0][P + "Type__c"] = "Number"
    else:
        source.links[0][P + "Selected_Order__c"] = "malformed"
    assert client.post(url + "/ingest", json={}, headers=ORIGIN).status_code == 409
    assert client.get(url + "/evidence").status_code == 404


def test_missing_answer_is_a_disclosed_gap_not_invented(evidence):
    client, url, source, _ = evidence
    source.rows.pop(0)
    response = client.post(url + "/ingest", json={}, headers=ORIGIN)
    assert response.status_code == 201
    answer = response.json()["answers"][0]
    assert answer["state"] == "missing" and answer["normalized_value"] is None
    assert "registered_name" in response.json()["gaps"]


def test_auth_tenant_and_csrf_boundaries(evidence, setup, businesses):
    client, url, _, _ = evidence
    assert client.post(url + "/ingest", json={}).status_code == 403
    client.post(url + "/ingest", json={}, headers=ORIGIN)
    foreign = url.replace(businesses[0], businesses[1])
    assert client.get(foreign + "/evidence").status_code == 404
    client = login(setup, "bob")
    assert client.get(url + "/evidence").status_code == 403
    assert client.post(url + "/ingest", json={}, headers=ORIGIN).status_code == 403
    client.cookies.clear()
    assert client.get(url + "/evidence").status_code == 401


def test_concurrent_ingestion_has_one_snapshot(evidence, setup, businesses):
    _, _, source, id_ = evidence

    def run(_):
        with Session(setup[1]) as db:
            return ingest(db, Principal("alice"), businesses[0], id_, source)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(run, range(2)))
    assert sorted(created for _, created in results) == [False, True]
    assert results[0][0]["id"] == results[1][0]["id"]
