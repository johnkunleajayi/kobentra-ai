import pytest
from test_business import ORIGIN, login
from workspace_fixtures import businesses as businesses
from workspace_fixtures import path
from workspace_fixtures import setup as setup


def test_opportunity_crud_retries_and_cross_business_ids(setup, businesses):
    client = login(setup)
    a, b = businesses
    payload = {"title": " Seeking distributors ", "stage": "exploring"}
    response = client.post(path(a, "/opportunities"), json=payload, headers=ORIGIN)
    assert response.status_code == 201
    record = response.json()
    assert record["organization_id"] == a and record["title"] == "Seeking distributors"
    retry = client.post(path(a, "/opportunities"), json=payload, headers=ORIGIN)
    assert retry.status_code == 200 and retry.json() == record
    assert client.get(path(a, "/opportunities")).json() == {"opportunities": [record]}
    assert client.get(path(b, "/opportunities")).json() == {"opportunities": []}
    target = path(a, "/opportunities/" + record["id"])
    assert client.get(target).json() == record
    result = client.put(target, json={"title": "Updated", "stage": "conversation"}, headers=ORIGIN)
    assert result.status_code == 200 and result.json()["stage"] == "conversation"
    assert client.get(target).json()["title"] == "Updated"
    foreign = path(b, "/opportunities/" + record["id"])
    assert client.get(foreign).status_code == 404
    assert client.put(foreign, json=payload, headers=ORIGIN).status_code == 404


@pytest.mark.parametrize(
    "payload",
    [
        {"title": " "},
        {"title": "x" * 161},
        {"title": "Sample", "stage": "bad"},
        {"title": "Sample", "organization_id": "other"},
        {"title": "Sample", "description": "unsupported"},
    ],
)
def test_invalid_opportunity(setup, businesses, payload):
    assert (
        login(setup)
        .post(path(businesses[0], "/opportunities"), json=payload, headers=ORIGIN)
        .status_code
        == 422
    )
