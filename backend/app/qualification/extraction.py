import json
import math

from .provider import MAPPING, P


class EvidenceConflict(ValueError):
    """Codes only; never include answers or question text in errors."""


def extract(parent, rows, junctions, choices):
    by_question, choice_map = {}, {row["Id"]: row for row in choices}
    if len(choice_map) != len(choices):
        raise EvidenceConflict("duplicate_choices")
    result_ids = {row["Id"] for row in rows}
    if len(result_ids) != len(rows) or any(
        j.get(P + "Question_Result__c") not in result_ids for j in junctions
    ):
        raise EvidenceConflict("invalid_result_links")
    for row in rows:
        qid = row.get(P + "Question__c")
        if (
            qid not in MAPPING["questions"]
            or qid in by_question
            or row.get(P + "Survey_Result__c") != parent
        ):
            raise EvidenceConflict("unexpected_duplicate_or_foreign_question")
        by_question[qid] = row
    evidence, gaps = [], []
    for qid, spec in MAPPING["questions"].items():
        row = by_question.get(qid)
        item = {
            "key": spec["key"],
            "question_id": qid,
            "question_result_id": row["Id"] if row else None,
            "parent_result_id": parent,
            "question_type": spec["type"],
            "extraction_version": MAPPING["extraction_version"],
            "provenance": "surveyvista_self_reported",
            "normalized_value": None,
            "raw_value": row,
            "raw_selections": [],
        }
        if row is None:
            item["state"] = "missing"
            gaps.append(spec["key"])
        else:
            links = [j for j in junctions if j[P + "Question_Result__c"] == row["Id"]]
            selected = []
            seen = set()
            for link in links:
                rank = link.get(P + "Selected_Order__c")
                if rank is not None and (
                    isinstance(rank, bool)
                    or not isinstance(rank, (int, float))
                    or not math.isfinite(rank)
                    or rank < 0
                ):
                    raise EvidenceConflict("invalid_selection_order")
                choice = choice_map.get(link.get(P + "Ans_Choice__c"))
                if not choice or choice.get(P + "Question__c") != qid or choice["Id"] in seen:
                    raise EvidenceConflict("invalid_choice_links")
                seen.add(choice["Id"])
                if (
                    not isinstance(choice.get(P + "Choice_Value__c"), str)
                    or not choice[P + "Choice_Value__c"].strip()
                ):
                    raise EvidenceConflict("invalid_choice_value")
                selected.append(
                    {
                        "choice_id": choice["Id"],
                        "value": choice.get(P + "Choice_Value__c"),
                        "label": choice.get(P + "Choice_Label__c"),
                    }
                )
            item["raw_selections"] = sorted(links, key=lambda r: r["Id"])
            answered = row.get(P + "Answered__c")
            if not isinstance(answered, bool):
                raise EvidenceConflict("invalid_answered_flag")
            if not answered:
                if selected or any(
                    row.get(P + f) is not None
                    for f in [
                        "Answer_Text__c",
                        "Answer_Value__c",
                        "Answer_Number__c",
                        "Answer_Polar__c",
                    ]
                ):
                    raise EvidenceConflict("unanswered_with_values")
                item["state"] = "unanswered"
                gaps.append(spec["key"])
            else:
                type_ = spec["type"]
                if type_ in {"Text-Short", "Text-Long"}:
                    value = row.get(P + "Answer_Text__c")
                    if selected or not isinstance(value, str) or not value.strip():
                        raise EvidenceConflict("invalid_text")
                    value = value.strip()
                elif type_ == "Number":
                    value = row.get(P + "Answer_Number__c")
                    if (
                        selected
                        or isinstance(value, bool)
                        or not isinstance(value, (int, float))
                        or not math.isfinite(value)
                        or value < 0
                    ):
                        raise EvidenceConflict("invalid_years")
                else:
                    if not selected or (type_ != "Multiple Choice" and len(selected) != 1):
                        raise EvidenceConflict("invalid_selection_count")
                    value = sorted(selected, key=lambda r: r["choice_id"])
                    if type_ == "Polar-Yes/No":
                        polar = row.get(P + "Answer_Polar__c")
                        if polar not in {"True", "False"} or selected[0]["value"] != polar:
                            raise EvidenceConflict("invalid_polar")
                        value = polar == "True"
                item.update(state="answered", normalized_value=value)
        evidence.append(item)
    # Reject oversized/non-JSON data rather than losing or truncating source evidence.
    if len(json.dumps(evidence, allow_nan=False)) > 200_000:
        raise EvidenceConflict("evidence_too_large")
    return evidence, gaps
