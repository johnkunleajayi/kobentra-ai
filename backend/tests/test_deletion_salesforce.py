import pytest
from deletion_salesforce_fixture import LEAD, DeletionSalesforce
from sqlalchemy.orm import Session
from test_admin import owner as owner
from test_business import ORIGIN
from test_business_deletion import confirmation
from workspace_fixtures import businesses as businesses
from workspace_fixtures import setup as setup

from app.assessments.dispatch import marker
from app.assessments.models import BusinessAssessment


@pytest.fixture
def linked(owner, setup, businesses):
    with Session(setup[1]) as db:
        a = BusinessAssessment(
            organization_id=businesses[0],
            business_id=businesses[0],
            initiated_by="alice",
            assessment_type="partner_qualification",
            provider_survey_id="test-survey",
            provider_logical_id="salesforce_flow",
            integration_mode="salesforce_flow",
            salesforce_lead_id=LEAD,
            correlation_id="test-opaque-correlation",
            dispatch_state="sent",
        )
        db.add(a)
        db.flush()
        expected = {
            "LastName": "Test",
            "Email": "fictional@example.invalid",
            "Company": "Fictional test",
            "Description": marker(a),
        }
        a.dispatch_payload = {"instance": DeletionSalesforce.origin, "lead": expected}
        db.commit()
    client = DeletionSalesforce(
        {"Id": LEAD, **expected, "IsDeleted": False, "IsConverted": False, "MasterRecordId": None}
    )
    setup[0].app.state.salesforce_client = client
    setup[0].app.state.settings.salesforce_business_deletion_enabled = True
    return client


def test_exact_link_recycled_then_local_cleanup_completes(owner, setup, businesses, linked):
    url = f"/api/admin/businesses/{businesses[0]}/deletion"
    body = confirmation(owner, businesses[0])
    response = owner.post(url, json=body, headers=ORIGIN)
    op = response.json()["operation"]
    assert op["state"] == "completed" and op["completed_at"]
    assert op["local_data_removed"] is True and linked.deletes == [LEAD]
    assert op["salesforce_outcome"] == "recycled_verified"
    assert owner.post(url, json=body, headers=ORIGIN).json()["operation"]["id"] == op["id"]
    assert (
        owner.post(url + "/retry", json={"operation_id": op["id"]}, headers=ORIGIN).json()[
            "operation"
        ]["state"]
        == "completed"
    )
    assert linked.deletes == [LEAD]
    assert owner.get(f"/api/admin/businesses/{businesses[0]}").status_code == 404


@pytest.mark.parametrize(
    "case",
    ["foreign_marker", "foreign_org", "missing", "converted", "cascade", "unavailable", "disabled"],
)
def test_unsafe_remote_deletion_fails_closed(owner, setup, businesses, linked, case):
    url = f"/api/admin/businesses/{businesses[0]}/deletion"
    body = confirmation(owner, businesses[0])
    if case == "foreign_marker":
        linked.row["Description"] = "Other assessment"
    if case == "foreign_org":
        linked.origin = "https://other.my.salesforce.com"
    if case == "missing":
        linked.row = None
    if case == "converted":
        linked.row["IsConverted"] = True
    if case == "cascade":
        linked.cascade = True
    if case == "unavailable":
        linked.unavailable = True
    if case == "disabled":
        setup[0].app.state.settings.salesforce_business_deletion_enabled = False
    response = owner.post(url, json=body, headers=ORIGIN)
    assert response.status_code in {200, 409, 503}
    if response.status_code == 200:
        assert response.json()["operation"]["state"] == "salesforce_retry"
    assert linked.deletes == []


def test_ambiguous_timeout_reconciles_deleted_identity_without_second_delete(
    owner, businesses, linked
):
    url = f"/api/admin/businesses/{businesses[0]}/deletion"
    body = confirmation(owner, businesses[0])
    linked.timeout_after_delete = True
    op = owner.post(url, json=body, headers=ORIGIN).json()["operation"]
    assert op["state"] == "salesforce_retry"
    retried = owner.post(url + "/retry", json={"operation_id": op["id"]}, headers=ORIGIN).json()[
        "operation"
    ]
    assert retried["state"] == "completed"
    assert linked.deletes == [LEAD]


def test_already_deleted_requires_exact_record_proof(owner, businesses, linked):
    linked.row["IsDeleted"] = True
    body = confirmation(owner, businesses[0])
    result = owner.post(
        f"/api/admin/businesses/{businesses[0]}/deletion", json=body, headers=ORIGIN
    )
    assert result.json()["operation"]["state"] == "completed"
    assert not linked.deletes


def test_restore_between_remote_checkpoint_and_cleanup_retains_local_data(
    owner, businesses, linked, monkeypatch
):
    from app.admin.deletion import service

    body = confirmation(owner, businesses[0])
    read = service.lead

    def restored(client, target):
        linked.row["IsDeleted"] = False
        return read(client, target)

    monkeypatch.setattr(service, "lead", restored)
    op = owner.post(
        f"/api/admin/businesses/{businesses[0]}/deletion", json=body, headers=ORIGIN
    ).json()["operation"]
    assert op["state"] == "salesforce_retry" and not op["local_data_removed"]
    assert owner.get(f"/api/admin/businesses/{businesses[0]}").status_code == 200
    assert linked.deletes == [LEAD]


@pytest.mark.parametrize("valid", [True, False])
def test_legacy_operation_revalidates_identity(owner, setup, businesses, linked, valid):
    from app.admin.deletion.models import DeletionOperation
    from app.admin.deletion.schemas import DeleteConfirmation
    from app.admin.deletion.service import initiate
    from app.security import Principal

    body = DeleteConfirmation(**confirmation(owner, businesses[0]))
    with Session(setup[1]) as db:
        op_id = initiate(
            db, Principal("alice"), setup[0].app.state.settings, businesses[0], body, linked
        )
        db.get(DeletionOperation, op_id).state = "awaiting_permanent_purge"
        db.commit()
    linked.row["IsDeleted"] = True
    if not valid:
        linked.row["Description"] = "Other business"
    op = owner.post(
        f"/api/admin/businesses/{businesses[0]}/deletion/retry",
        json={"operation_id": op_id},
        headers=ORIGIN,
    ).json()["operation"]
    assert op["state"] == ("completed" if valid else "salesforce_retry")
    assert op["local_data_removed"] is valid
    assert not linked.deletes


def test_remote_checkpoint_survives_local_cleanup_failure(
    owner, setup, businesses, linked, monkeypatch
):
    from sqlalchemy.exc import OperationalError

    from app.admin.deletion import service

    url = f"/api/admin/businesses/{businesses[0]}/deletion"
    body = confirmation(owner, businesses[0])
    original = service.purge

    def fail(db, business_id):
        original(db, business_id)
        raise OperationalError("test", {}, None)

    monkeypatch.setattr(service, "purge", fail)
    assert owner.post(url, json=body, headers=ORIGIN).status_code == 503
    op = owner.get(url).json()["operation"]
    assert op["state"] == "local_pending" and not op["local_data_removed"]
    assert op["salesforce_outcome"] == "recycled_verified"
    assert owner.get(f"/api/admin/businesses/{businesses[0]}").status_code == 200
    monkeypatch.setattr(service, "purge", original)
    assert (
        owner.post(url + "/retry", json={"operation_id": op["id"]}, headers=ORIGIN).json()[
            "operation"
        ]["state"]
        == "completed"
    )
    assert linked.deletes == [LEAD]


@pytest.mark.parametrize("case", ["permission", "ambiguous_response"])
def test_unverified_delete_response_never_cleans_up(owner, businesses, linked, monkeypatch, case):
    from app.salesforce.client import SalesforceError

    body = confirmation(owner, businesses[0])
    request = linked.request

    def respond(method, path, **kwargs):
        if method == "DELETE":
            if case == "permission":
                raise SalesforceError("Denied")
            return {}
        return request(method, path, **kwargs)

    monkeypatch.setattr(linked, "request", respond)
    op = owner.post(
        f"/api/admin/businesses/{businesses[0]}/deletion", json=body, headers=ORIGIN
    ).json()["operation"]
    assert op["state"] == "salesforce_retry" and not op["local_data_removed"]
    assert op["completed_at"] is None
