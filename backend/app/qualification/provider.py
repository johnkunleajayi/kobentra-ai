import hashlib
import json
from pathlib import Path

from ..salesforce.client import SalesforceError
from ..salesforce.results import sf_id

MAPPING = json.loads(Path(__file__).with_name("mapping.json").read_text())
P = "ArdiraSurvey__"
RESULT_FIELDS = [
    "Id",
    P + "Survey_Result__c",
    P + "Question__c",
    P + "Answered__c",
    P + "Answer_Text__c",
    P + "Answer_Value__c",
    P + "Answer_Number__c",
    P + "Answer_Polar__c",
    P + "Question_Display_Order__c",
]


def fetch_answers(client, record):
    parent = sf_id(record.provider_response_id)
    # Re-read the exact bound parent, never discover answers by Lead alone.
    source = client.request(
        "GET", f"/services/data/v68.0/sobjects/ArdiraSurvey__Survey_Result__c/{parent}"
    )
    if source.get("Id") != parent or source.get(P + "Target_Lead__c") != record.salesforce_lead_id:
        raise SalesforceError("Parent evidence mismatch")
    fields = client.request(
        "GET", "/services/data/v68.0/sobjects/ArdiraSurvey__Survey_Result__c/describe"
    )["fields"]
    status = [
        f["name"]
        for f in fields
        if any(
            p.get("active") and p.get("value") == "Completed" for p in f.get("picklistValues", [])
        )
    ]
    configured = client.settings.salesforce_result_status_field
    if configured:
        status = [f for f in status if f == configured]
    survey_fields = []
    for field in fields:
        for target in field.get("referenceTo", []):
            # Salesforce object metadata is still validated before URL construction.
            if not target.replace("_", "").isalnum():
                raise SalesforceError("Invalid metadata")
            meta = client.request("GET", f"/services/data/v68.0/sobjects/{target}/describe")
            if meta.get("keyPrefix") == MAPPING["survey_id"][:3]:
                survey_fields.append(field["name"])
    configured = client.settings.salesforce_result_survey_field
    if configured:
        survey_fields = [f for f in survey_fields if f == configured]
    if (
        len(status) != 1
        or len(survey_fields) != 1
        or source.get(status[0]) != "Completed"
        or source.get(survey_fields[0]) != record.provider_survey_id
    ):
        raise SalesforceError("Parent completion/survey mismatch")
    from datetime import datetime, timezone

    completed = datetime.fromisoformat(source[P + "Response_End_Time__c"].replace("Z", "+00:00"))
    stored = record.completed_at
    if stored.tzinfo is None:
        stored = stored.replace(tzinfo=timezone.utc)
    if completed.tzinfo is None or completed != stored:
        raise SalesforceError("Parent completion changed")
    rows = client.query(
        f"SELECT {', '.join(RESULT_FIELDS)} FROM ArdiraSurvey__Question_Result__c WHERE {P}Survey_Result__c = '{parent}'"
    )
    ids = [sf_id(row["Id"]) for row in rows]
    if (
        len(ids) > 10
        or len(ids) != len(set(ids))
        or any(row.get(P + "Survey_Result__c") != parent for row in rows)
    ):
        raise SalesforceError("Unexpected or duplicate result rows")
    question_ids = list(MAPPING["questions"])
    quoted = ",".join("'" + sf_id(i) + "'" for i in question_ids)
    questions = client.query(
        f"SELECT Id, {P}Survey__c, {P}Question_Plain_Text__c, {P}Type__c FROM ArdiraSurvey__Question__c WHERE Id IN ({quoted})"
    )
    if len(questions) != 10 or len({q["Id"] for q in questions}) != 10:
        raise SalesforceError("Question metadata incomplete")
    for q in questions:
        expected = MAPPING["questions"].get(q["Id"])
        if (
            not expected
            or q.get(P + "Survey__c") != MAPPING["survey_id"]
            or q.get(P + "Type__c") != expected["type"]
            or hashlib.sha256((q.get(P + "Question_Plain_Text__c") or "").encode()).hexdigest()
            != expected["definition_hash"]
        ):
            raise SalesforceError("Question mapping changed")
    choices = client.query(
        f"SELECT Id, {P}Question__c, {P}Choice_Label__c, {P}Choice_Value__c FROM ArdiraSurvey__Answer_Choice__c WHERE {P}Question__c IN ({quoted})"
    )
    junctions = (
        client.query(
            f"SELECT Id, {P}Question_Result__c, {P}Ans_Choice__c, {P}Selected_Order__c FROM ArdiraSurvey__Question_Result_Choice__c WHERE {P}Question_Result__c IN ("
            + ",".join("'" + i + "'" for i in ids)
            + ")"
        )
        if ids
        else []
    )
    return rows, junctions, choices
