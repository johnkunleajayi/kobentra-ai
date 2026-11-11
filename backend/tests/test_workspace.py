import pytest
from sqlalchemy.orm import Session
from test_business import ORIGIN, login
from workspace_fixtures import businesses as businesses
from workspace_fixtures import path
from workspace_fixtures import setup as setup

from app.models import Membership


def test_workspace_listing_and_authorization(setup, businesses):
    client = login(setup)
    assert len(client.get("/api/businesses").json()["businesses"]) == 2
    for business in businesses:
        response = client.get(path(business))
        assert response.status_code == 200 and response.json()["organization_id"] == business
    client = login(setup, "bob")
    assert client.get(path(businesses[0])).status_code == 403
    assert client.get(path("missing")).status_code == 403


@pytest.mark.parametrize("role", [None, "member", "admin"])
def test_membership_roles_apply_to_every_endpoint(setup, businesses, role):
    a, _ = businesses
    owner = login(setup)
    record = owner.post(path(a, "/opportunities"), json={"title": "Sample"}, headers=ORIGIN).json()
    if role:
        with Session(setup[1]) as db:
            db.add(Membership(user_id="bob", organization_id=a, role=role))
            db.commit()
    client = login(setup, "bob")
    detail = path(a, "/opportunities/" + record["id"])
    for url in [path(a), path(a, "/market-preferences"), path(a, "/opportunities"), detail]:
        assert client.get(url).status_code == (200 if role else 403)
    writes = [
        ("PUT", path(a, "/market-preferences"), {"preferences": []}),
        ("POST", path(a, "/opportunities"), {"title": "New"}),
        ("PUT", detail, {"title": "Updated", "stage": "closed"}),
    ]
    for method, url, payload in writes:
        response = client.request(method, url, json=payload, headers=ORIGIN)
        assert (response.status_code < 300) if role == "admin" else response.status_code == 403


def test_csrf_and_anonymous_access(setup, businesses):
    client = login(setup)
    a, _ = businesses
    for method, url, payload in [
        ("PUT", path(a, "/market-preferences"), {"preferences": []}),
        ("POST", path(a, "/opportunities"), {"title": "Sample"}),
    ]:
        assert client.request(method, url, json=payload).status_code == 403
        client.cookies.clear()
        assert client.request(method, url, json=payload, headers=ORIGIN).status_code == 401
        login(setup)
    client.cookies.clear()
    assert client.get(path(a)).status_code == 401
    assert client.get(path(a, "/market-preferences")).status_code == 401
    assert client.get(path(a, "/opportunities")).status_code == 401
