from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import pytest
from salesforce_fixtures import LEAD, RESULT
from salesforce_fixtures import businesses as businesses
from salesforce_fixtures import native as native
from salesforce_fixtures import setup as setup
from sqlalchemy.orm import Session
from test_business import ORIGIN, login

from app.assessments.dispatch import SURVEY_ID, dispatch
from app.assessments.schemas import DispatchAssessment
from app.security import Principal

RECIPIENT = {"last_name": "Sample", "email": "sample@example.invalid"}


def test_server_failure_and_empty_reconciliation_never_resend(native):
    client, url, state, _ = native
    state["fail_status"] = True
    assert (
        client.post(url + "/dispatch", json=RECIPIENT, headers=ORIGIN).json()["dispatch_state"]
        == "uncertain"
    )
    state["leads"] = []
    assert client.post(url + "/sync", json={}, headers=ORIGIN).json()["completed_at"] is None
    client.post(url + "/dispatch", json=RECIPIENT, headers=ORIGIN)
    assert state["posts"] == 1


def test_duplicate_markers_refuse_association(native):
    client, url, state, _ = native
    state["fail"] = True
    client.post(url + "/dispatch", json=RECIPIENT, headers=ORIGIN)
    state["leads"].append({**state["leads"][0], "Id": "00Q000000000002AAA"})
    assert client.post(url + "/sync", json={}, headers=ORIGIN).status_code == 503
    assert client.get(url).json()["salesforce_lead_id"] is None


def test_dispatch_retries_and_tenant_isolation(native, setup, businesses):
    client, url, state, _ = native
    first = client.post(url + "/dispatch", json=RECIPIENT, headers=ORIGIN)
    assert first.status_code == 200 and first.json()["salesforce_lead_id"] == LEAD
    assert first.json()["dispatch_state"] == "sent"
    assert state["leads"][0]["Kobentra_Assessment_Requested__c"] is True
    assert "correlation" in state["leads"][0]["Description"]
    assert client.post(url + "/dispatch", json=RECIPIENT, headers=ORIGIN).status_code == 200
    assert state["posts"] == 1
    assert (
        client.post(
            url + "/dispatch", json={**RECIPIENT, "last_name": "Changed"}, headers=ORIGIN
        ).status_code
        == 409
    )
    assert client.post(url + "/launch", json={}, headers=ORIGIN).status_code == 409
    client = login(setup, "bob")
    assert client.post(url + "/dispatch", json=RECIPIENT, headers=ORIGIN).status_code == 403
    assert client.post(url + "/sync", json={}, headers=ORIGIN).status_code == 403


def test_ambiguous_timeout_reconciles_without_resend(native):
    client, url, state, _ = native
    state["fail"] = True
    assert (
        client.post(url + "/dispatch", json=RECIPIENT, headers=ORIGIN).json()["dispatch_state"]
        == "uncertain"
    )
    assert client.post(url + "/dispatch", json=RECIPIENT, headers=ORIGIN).status_code == 200
    reconciled = client.post(url + "/sync", json={}, headers=ORIGIN)
    assert reconciled.status_code == 200 and reconciled.json()["salesforce_lead_id"] == LEAD
    assert reconciled.json()["status"] == "launch_requested" and state["posts"] == 1


def test_concurrent_dispatch_has_one_durable_send(native, setup, businesses):
    _, url, state, sf = native
    assessment_id = url.rsplit("/", 1)[1]

    def send(_):
        with Session(setup[1]) as db:
            return dispatch(
                db,
                Principal("alice"),
                businesses[0],
                assessment_id,
                DispatchAssessment(**RECIPIENT),
                setup[0].app.state.settings,
                sf,
            )

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(send, range(2)))
    assert state["posts"] == 1


@pytest.mark.parametrize(
    "change",
    [
        {"VerifiedStatus__c": "Started"},
        {"ArdiraSurvey__Response_End_Time__c": None},
        {"VerifiedSurvey__c": "a0Z000000000002AAA"},
        {"ArdiraSurvey__Target_Lead__c": "00Q000000000002AAA"},
    ],
)
def test_incomplete_or_mismatched_evidence_never_verifies(native, change):
    client, url, state, _ = native
    client.post(url + "/dispatch", json=RECIPIENT, headers=ORIGIN)
    result = {
        "Id": RESULT,
        "VerifiedSurvey__c": SURVEY_ID,
        "VerifiedStatus__c": "Completed",
        "ArdiraSurvey__Target_Lead__c": LEAD,
        "ArdiraSurvey__Response_End_Time__c": datetime.now(timezone.utc).isoformat(),
    }
    result.update(change)
    state["results"] = [result]
    response = client.post(url + "/sync", json={}, headers=ORIGIN)
    if response.status_code == 200:
        assert response.json()["status"] != "completed_verified"
    else:
        assert response.status_code == 503
    assert client.get(url).json()["completed_at"] is None


def test_authoritative_completion(native):
    client, url, state, _ = native
    client.post(url + "/dispatch", json=RECIPIENT, headers=ORIGIN)
    state["results"] = [
        {
            "Id": RESULT,
            "VerifiedSurvey__c": SURVEY_ID,
            "VerifiedStatus__c": "Completed",
            "ArdiraSurvey__Target_Lead__c": LEAD,
            "ArdiraSurvey__Response_End_Time__c": datetime.now(timezone.utc).isoformat(),
        }
    ]
    response = client.post(url + "/sync", json={}, headers=ORIGIN)
    assert response.status_code == 200
    assert response.json()["status"] == "completed_verified"
    assert response.json()["provider_response_id"] == RESULT
    assert response.json()["completed_at"] and response.json()["synchronized_at"]
