"""Validate pinned normalized evidence without interpreting question HTML or raw answers."""

import json
import math

from .provider import MAPPING


def valid_value(value, kind):
    if kind in {"Text-Short", "Text-Long"}:
        return isinstance(value, str) and bool(value.strip())
    if kind == "Number":
        return (
            not isinstance(value, bool)
            and isinstance(value, (int, float))
            and math.isfinite(value)
            and value >= 0
        )
    if kind == "Polar-Yes/No":
        return isinstance(value, bool)
    return (
        isinstance(value, list)
        and bool(value)
        and (kind == "Multiple Choice" or len(value) == 1)
        and all(
            isinstance(v, dict)
            and isinstance(v.get("choice_id"), str)
            and isinstance(v.get("value"), str)
            and bool(v["value"].strip())
            for v in value
        )
        and len({v["choice_id"] for v in value}) == len(value)
    )


def canonical(value):
    # Labels and selection order do not define claim identity.
    if isinstance(value, list):
        value = sorted(v["value"].strip().casefold() for v in value)
    elif isinstance(value, str):
        value = " ".join(value.split()).casefold()
    return json.dumps(value, sort_keys=True)


def collect(snapshots):
    values, conflicts, issues = {}, set(), set()
    specs = {s["key"]: (qid, s["type"]) for qid, s in MAPPING["questions"].items()}
    for row in snapshots:
        if (
            row.extraction_version != MAPPING["extraction_version"]
            or row.evidence_kind != "self_reported"
        ):
            issues.add("unsupported_evidence_version")
            continue
        if not isinstance(row.answers, list):
            issues.add("malformed_evidence")
            continue
        seen = set()
        for item in row.answers:
            if (
                not isinstance(item, dict)
                or not isinstance(item.get("key"), str)
                or item["key"] not in specs
            ):
                issues.add("unexpected_evidence")
                continue
            key = item["key"]
            qid, kind = specs[key]
            if key in seen:
                conflicts.add(key)
            seen.add(key)
            if (
                item.get("question_id") != qid
                or item.get("question_type") != kind
                or item.get("parent_result_id") != row.provider_response_id
                or item.get("extraction_version") != row.extraction_version
                or item.get("provenance") != "surveyvista_self_reported"
            ):
                conflicts.add(key)
                continue
            if item.get("state") != "answered":
                continue
            value = item.get("normalized_value")
            if (
                not valid_value(value, kind)
                or not isinstance(item.get("question_result_id"), str)
                or not item["question_result_id"].strip()
            ):
                issues.add("malformed_" + key)
                conflicts.add(key)
                continue
            if key in values and canonical(values[key]) != canonical(value):
                conflicts.add(key)
            values[key] = value
    return {k: v for k, v in values.items() if k not in conflicts}, conflicts, issues
