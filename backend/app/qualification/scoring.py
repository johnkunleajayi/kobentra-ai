"""Pure, deterministic provisional rubric. Never grants verification or authorization."""

import json
from pathlib import Path

from .provider import MAPPING
from .scoring_inputs import canonical, collect

RULES = json.loads(Path(__file__).with_name("scoring.json").read_text(encoding="utf-8"))


def evaluate(snapshots, profile, preferences, rules=None):
    rules = rules or RULES
    values, conflicts, issues = collect(snapshots)
    answered_count = len(values)
    # Compare only equivalent explicit fields; market targets are not markets served.
    if profile and "registered_name" in values:
        if canonical(profile.name) != canonical(values["registered_name"]):
            conflicts.add("registered_name")
            values.pop("registered_name")
    keys = [s["key"] for s in MAPPING["questions"].values()]
    gaps = [
        {
            "code": "conflicting_" + k,
            "recommendation": "Review conflicting claims before relying on this field.",
        }
        for k in sorted(conflicts)
    ]
    gaps += [
        {"code": "unknown_" + k, "recommendation": "Provide or clarify this assessment answer."}
        for k in keys
        if k not in values and k not in conflicts
    ]
    gaps += [
        {"code": i, "recommendation": "Review evidence format or extraction version."}
        for i in sorted(issues)
    ]
    if not profile or any(
        not getattr(profile, k, None) for k in ("name", "country", "sector", "goal")
    ):
        gaps.append(
            {"code": "profile_incomplete", "recommendation": "Complete the business profile."}
        )
    if not preferences:
        gaps.append(
            {
                "code": "market_preferences_missing",
                "recommendation": "Set target countries and partnership interests.",
            }
        )
    dimensions = []
    for name, spec in rules["dimensions"].items():
        reasons, points = [], []
        for key in spec["keys"]:
            point = None
            reason = "Unknown or disputed; excluded, not scored as zero."
            if key in values:
                point = rules["declared_score"]
                reason = (
                    "Self-reported declaration; quality, scale and suitability are not verified."
                )
                if key in {"registered_name", "primary_country"}:
                    point = rules["identity_score"]
                    reason = (
                        "Identity field supplied; completeness only, not identity verification."
                    )
                elif key == "years_operating":
                    reason = (
                        "Operating history declared; zero years is valid and age earns no bonus."
                    )
                elif key == "cross_border_experience":
                    if values[key] is False:
                        point = rules["no_cross_border_score"]
                    reason = (
                        "Declared experience informs preparation; absence is not business failure."
                    )
                points.append(point)
            reasons.append({"key": key, "score": point, "reason": reason})
        dimensions.append(
            {
                "dimension": name,
                "weight": spec["weight"],
                "score": round(sum(points) / len(points), 2) if points else None,
                "known_answers": len(points),
                "expected_answers": len(spec["keys"]),
                "reasons": reasons,
            }
        )
    # Use known question-weight only; unknown fields never dilute a score with zeros.
    numerator = denominator = 0
    for d in dimensions:
        weight = d["weight"] / d["expected_answers"]
        for reason in d["reasons"]:
            if reason["score"] is not None:
                numerator += weight * reason["score"]
                denominator += weight
    score = round(numerator / denominator, 2) if denominator else None
    classification = next(
        (label for minimum, label in rules["thresholds"] if score is not None and score >= minimum),
        None,
    )
    return {
        "readiness": {
            "version": rules["version"],
            "score": score,
            "classification": classification,
            "provisional": True,
            "notice": "Declared preparedness indicator, not a validated risk rating or partner-fit judgment.",
            "dimensions": dimensions,
            "scored_weight_percent": denominator,
        },
        "completeness": {
            "answered": answered_count,
            "expected": len(keys),
            "percent": round(100 * answered_count / len(keys), 2),
            "usable_for_scoring": len(values),
        },
        "confidence": {
            "classification": "conflicting" if conflicts else "self_reported",
            "supported_classifications": [
                "self_reported",
                "partially_supported",
                "verified_for_specified_claims",
                "conflicting",
            ],
            "independently_verified_claims": [],
            "conflicting_claims": sorted(conflicts),
            "reason": "No independent supporting-evidence source is connected.",
        },
        "qualification_gaps": gaps,
        "recommendations": [g["recommendation"] for g in gaps],
    }
