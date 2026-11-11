from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy.orm import Session
from test_business import ORIGIN, login
from workspace_fixtures import businesses as businesses
from workspace_fixtures import path
from workspace_fixtures import setup as setup

from app.assessments.constants import PUBLIC_URL
from app.assessments.service import initiate
from app.security import Principal


def endpoint(business, suffix=""):
    return path(business, "/assessments" + suffix)


def test_authenticated_initiation_launch_and_no_false_completion(setup, businesses):
    client = login(setup)
    url = endpoint(businesses[0])
    created = client.post(url, json={}, headers=ORIGIN)
    assert created.status_code == 201
    record = created.json()
    assert record["organization_id"] == record["business_id"] == businesses[0]
    assert record["status"] == "initiated" and record["completed_at"] is None
    assert client.get(url + "/" + record["id"]).json() == record
    duplicate = client.post(url, json={}, headers=ORIGIN)
    assert duplicate.status_code == 200 and duplicate.json()["id"] == record["id"]
    launch = client.post(url + "/" + record["id"] + "/launch", json={}, headers=ORIGIN)
    assert launch.status_code == 200
    assert launch.json()["launch_url"] == PUBLIC_URL
    assert launch.json()["unique_tracking_link"] is False
    assert launch.json()["assessment"]["status"] == "launch_requested"
    # Reopening, retrying, refreshing and 'returning' cannot supply completion evidence.
    again = client.post(url + "/" + record["id"] + "/launch", json={}, headers=ORIGIN)
    assert again.json() == launch.json()
    history = client.get(url).json()["assessments"]
    assert len(history) == 1 and history[0]["provider_response_id"] is None
    assert history[0]["completed_at"] is None and history[0]["synchronized_at"] is None


def test_cross_tenant_and_unknown_record_access(setup, businesses):
    client = login(setup)
    a, b = businesses
    record = client.post(endpoint(a), json={}, headers=ORIGIN).json()
    assert client.get(endpoint(b)).json() == {"assessments": []}
    assert client.get(endpoint(b, "/" + record["id"])).status_code == 404
    assert (
        client.post(
            endpoint(b, "/" + record["id"] + "/launch"), json={}, headers=ORIGIN
        ).status_code
        == 404
    )
    client = login(setup, "bob")
    assert client.get(endpoint(a)).status_code == 403
    assert client.get(endpoint(a, "/config")).status_code == 403
    assert client.get(endpoint(a, "/" + record["id"])).status_code == 403
    assert client.post(endpoint(a), json={}, headers=ORIGIN).status_code == 403


@pytest.mark.parametrize(
    "payload",
    [
        {"provider_response_id": "forged"},
        {"status": "completed_verified"},
        {"business_id": "other"},
        {"completed_at": "2026-11-10"},
        {"assessment_type": "invented"},
    ],
)
def test_client_cannot_assign_provider_identity_or_completion(setup, businesses, payload):
    client = login(setup)
    url = endpoint(businesses[0])
    assert client.post(url, json=payload, headers=ORIGIN).status_code == 422
    record = client.post(url, json={}, headers=ORIGIN).json()
    assert (
        client.post(url + "/" + record["id"] + "/launch", json=payload, headers=ORIGIN).status_code
        == 422
    )
    assert client.put(url + "/" + record["id"], json=payload, headers=ORIGIN).status_code == 405


def test_missing_config_and_changed_survey_fail_closed(setup, businesses):
    client = login(setup)
    url = endpoint(businesses[0])
    record = client.post(url, json={}, headers=ORIGIN).json()
    settings = client.app.state.settings
    settings.surveyvista_launch_url = None
    assert client.get(url + "/config").json()["configured"] is False
    assert client.post(url, json={}, headers=ORIGIN).status_code == 503
    assert (
        client.post(url + "/" + record["id"] + "/launch", json={}, headers=ORIGIN).status_code
        == 503
    )
    settings.surveyvista_launch_url = PUBLIC_URL.replace("a0Zaj00000JUZOn", "different")
    assert (
        client.post(url + "/" + record["id"] + "/launch", json={}, headers=ORIGIN).status_code
        == 409
    )
    assert client.get(url + "/" + record["id"]).json()["status"] == "initiated"


def test_auth_csrf_and_read_only_membership(setup, businesses):
    from app.models import Membership

    client = login(setup)
    url = endpoint(businesses[0])
    assert client.post(url, json={}).status_code == 403
    client.cookies.clear()
    assert client.post(url, json={}, headers=ORIGIN).status_code == 401
    assert client.get(url).status_code == 401
    with Session(setup[1]) as db:
        db.add(Membership(user_id="bob", organization_id=businesses[0], role="member"))
        db.commit()
    client = login(setup, "bob")
    assert client.get(url).status_code == 200
    assert client.post(url, json={}, headers=ORIGIN).status_code == 403


def test_concurrent_initiation_reuses_pending_assessment(setup, businesses):
    def start(_):
        with Session(setup[1]) as db:
            return initiate(db, Principal("alice"), businesses[0], setup[0].app.state.settings)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(start, range(2)))
    assert sorted(created for _, created in results) == [False, True]
    assert results[0][0].id == results[1][0].id
