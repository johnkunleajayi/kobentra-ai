import re
from datetime import datetime, timezone

from .client import SalesforceError


def sf_id(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9]{18}", value):
        raise SalesforceError("Invalid Salesforce identifier")
    return value


def completed_result(client, lead_id, survey_id):
    lead_id, survey_id = sf_id(lead_id), sf_id(survey_id)
    # Resolve package field API names from authoritative org Describe metadata.
    fields = client.request(
        "GET", "/services/data/v68.0/sobjects/ArdiraSurvey__Survey_Result__c/describe"
    )["fields"]
    status = [
        f["name"]
        for f in fields
        if any(
            p.get("value") == "Completed" and p.get("active") for p in f.get("picklistValues", [])
        )
    ]
    survey_fields = []
    for field in fields:
        for target in field.get("referenceTo", []):
            if not re.fullmatch(r"[A-Za-z0-9_]+", target):
                raise SalesforceError("Invalid object metadata")
            description = client.request("GET", f"/services/data/v68.0/sobjects/{target}/describe")
            if description.get("keyPrefix") == survey_id[:3]:
                survey_fields.append(field["name"])
    if client.settings.salesforce_result_status_field:
        status = [name for name in status if name == client.settings.salesforce_result_status_field]
    if client.settings.salesforce_result_survey_field:
        survey_fields = [
            name for name in survey_fields if name == client.settings.salesforce_result_survey_field
        ]
    if len(status) != 1 or len(set(survey_fields)) != 1:
        raise SalesforceError("Survey/status field metadata requires administrator verification")
    status_field, survey_field = status[0], survey_fields[0]
    if not all(re.fullmatch(r"[A-Za-z0-9_]+", f) for f in [status_field, survey_field]):
        raise SalesforceError("Invalid field metadata")
    rows = client.query(
        f"SELECT Id, ArdiraSurvey__Target_Lead__c, {survey_field}, {status_field}, ArdiraSurvey__Response_End_Time__c FROM ArdiraSurvey__Survey_Result__c WHERE ArdiraSurvey__Target_Lead__c = '{lead_id}' AND {survey_field} = '{survey_id}'"
    )
    valid = []
    for row in rows:
        if row.get("ArdiraSurvey__Target_Lead__c") != lead_id or row.get(survey_field) != survey_id:
            raise SalesforceError("Mismatched SurveyVista result")
        if row.get(status_field) != "Completed":
            continue
        try:
            stamp = datetime.fromisoformat(
                row["ArdiraSurvey__Response_End_Time__c"].replace("Z", "+00:00")
            )
            if stamp.tzinfo is None or stamp > datetime.now(timezone.utc):
                raise ValueError
            valid.append((sf_id(row["Id"]), stamp))
        except (ValueError, TypeError, KeyError, AttributeError):
            raise SalesforceError("Invalid completion evidence") from None
    if len(valid) > 1:
        raise SalesforceError("Multiple completed responses require review")
    return valid[0] if valid else None
