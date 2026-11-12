"""Verify exact org/correlation and move only the bound Lead to the Recycle Bin."""

import hashlib
import json
import re

from ...assessments.dispatch import marker
from ...salesforce.client import SalesforceError
from ...salesforce.results import sf_id


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def org_id(client):
    rows = client.query("SELECT Id FROM Organization LIMIT 2")
    if len(rows) != 1 or not sf_id(rows[0]["Id"]).startswith("00D"):
        raise SalesforceError("Salesforce organization cannot be established")
    return rows[0]["Id"]


def lead(client, target):
    if client.origin != target["origin"] or org_id(client) != target["org_id"]:
        raise SalesforceError("Salesforce organization mismatch")
    lead_id = sf_id(target["lead_id"])
    page = client.request(
        "GET",
        "/services/data/v68.0/queryAll",
        params={
            "q": f"SELECT Id, Description, LastName, Email, Company, IsDeleted, IsConverted, MasterRecordId FROM Lead WHERE Id = '{lead_id}' LIMIT 2"
        },
    )
    rows = page.get("records")
    if page.get("done") is not True or not isinstance(rows, list) or len(rows) != 1:
        raise SalesforceError("Missing is not proof of deletion")
    row = rows[0]
    if (
        row.get("Id") != lead_id
        or row.get("IsConverted") is not False
        or row.get("MasterRecordId") is not None
        or not isinstance(row.get("IsDeleted"), bool)
    ):
        raise SalesforceError("Unexpected Lead identity or state")
    if (
        digest({k: row.get(k) for k in ("Id", "Description", "LastName", "Email", "Company")})
        != target["binding_hash"]
    ):
        raise SalesforceError("Lead linkage mismatch")
    return row


def target_for(client, assessment):
    if (
        assessment.integration_mode != "salesforce_flow"
        or assessment.dispatch_state != "sent"
        or not assessment.correlation_id
    ):
        raise SalesforceError("Dispatch linkage is not settled")
    stored = assessment.dispatch_payload or {}
    if stored.get("instance") != client.origin or not sf_id(
        assessment.salesforce_lead_id
    ).startswith("00Q"):
        raise SalesforceError("Dispatch organization mismatch")
    expected = stored.get("lead", {})
    if expected.get("Description") != marker(assessment) or any(
        not expected.get(k) for k in ("LastName", "Email", "Company")
    ):
        raise SalesforceError("Dispatch correlation mismatch")
    target = {
        "origin": client.origin,
        "org_id": org_id(client),
        "lead_id": assessment.salesforce_lead_id,
        "binding_hash": digest(
            {
                "Id": assessment.salesforce_lead_id,
                **{k: expected[k] for k in ("Description", "LastName", "Email", "Company")},
            }
        ),
    }
    if not lead(client, target)["IsDeleted"]:
        check_cascades(client, target["lead_id"])
    return target


def check_cascades(client, lead_id):
    meta = client.request("GET", "/services/data/v68.0/sobjects/Lead/describe")
    children = meta.get("childRelationships")
    if not isinstance(children, list) or meta.get("deletable") is not True:
        raise SalesforceError("Lead deletion metadata unavailable")
    if any(
        not isinstance(child, dict) or not isinstance(child.get("cascadeDelete"), bool)
        for child in children
    ):
        raise SalesforceError("Incomplete cascade metadata")
    cascades = [c for c in children if c.get("cascadeDelete") is True]
    if len(cascades) > 30:
        raise SalesforceError("Deletion relationship review required")
    for child in cascades:
        obj, field = child.get("childSObject", ""), child.get("field", "")
        if not all(re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", value) for value in (obj, field)):
            raise SalesforceError("Unsupported cascade relationship")
        if client.query(f"SELECT Id FROM {obj} WHERE {field} = '{sf_id(lead_id)}' LIMIT 1"):
            raise SalesforceError("Related cascading records require separate review")


def recycle(client, target):
    row = lead(client, target)
    if not row["IsDeleted"]:
        check_cascades(client, target["lead_id"])
        client.request("DELETE", f"/services/data/v68.0/sobjects/Lead/{sf_id(target['lead_id'])}")
    if lead(client, target)["IsDeleted"] is not True:
        raise SalesforceError("Lead deletion not verified")
