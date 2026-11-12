"""Score declared compatibility, never readiness or independent verification."""

import json
from pathlib import Path

from .signals import industry, interests, operations, timing

RULES = json.loads(Path(__file__).with_name("rules.json").read_text(encoding="utf-8"))


def normalized(value):
    return " ".join(value.split()).casefold() if isinstance(value, str) else ""


def compare(source, partner, rules=None):
    """Compare internal normalized features; disclose only derived explanations.

    Raw answers, readiness and contact details must never enter the response.
    Conflicting dimensions are unknown, never a favorable match.
    """
    rules = rules or RULES
    dimensions = []

    def add(key, state, reason, fraction=1):
        known = state != "unknown"
        dimensions.append(
            {
                "dimension": key,
                "state": state,
                "reason": reason,
                "weight": rules["weights"][key],
                "known_weight": rules["weights"][key] * fraction if known else 0,
                "score": (100 if state == "compatible" else 0) if known else None,
            }
        )

    a, b = (
        interests(source, partner["country"], rules),
        interests(partner, source["country"], rules),
    )
    complements = {frozenset(p) for p in rules["complementary_intents"]}
    complementary = any(frozenset((x, y)) in complements for x in a for y in b)
    # An unrecognized term may describe a valid relationship; never interpret it as rejection.
    add(
        "intent",
        "compatible" if complementary else "unknown",
        "Declared partnership interests are complementary; ability to supply is not established."
        if complementary
        else "No documented complementary intent pair is established.",
    )
    add("industry_capability", *industry(source, partner, complementary, rules))
    source_targets = {normalized(p["country"]) for p in source["preferences"]}
    partner_targets = {normalized(p["country"]) for p in partner["preferences"]}
    # Require reciprocal expressed market interest; country is a base, not proof of coverage.
    if source_targets and partner_targets and source["country"] and partner["country"]:
        reciprocal = (
            normalized(partner["country"]) in source_targets
            and normalized(source["country"]) in partner_targets
        )
        add(
            "geography",
            "compatible" if reciprocal else "incompatible",
            "Reciprocal target-country interest; delivery coverage is unverified."
            if reciprocal
            else "Current declared target-country lists do not show reciprocal interest.",
        )
    else:
        add("geography", "unknown", "Reciprocal target-country preferences are incomplete.")
    add("operations", *operations(source, partner, rules))
    add("timing", *timing(source, partner, rules))
    conflicts = set(source.get("conflicts", ())) | set(partner.get("conflicts", ()))
    for d in dimensions:
        if d["dimension"] in conflicts:
            d.update(
                state="unknown",
                score=None,
                known_weight=0,
                reason="Conflicting information; excluded pending clarification.",
            )
    coverage = sum(d["known_weight"] for d in dimensions)
    sufficient = (
        coverage >= rules["minimum_coverage"]
        and sum(d["score"] is not None for d in dimensions) >= rules["minimum_dimensions"]
    )
    score = (
        round(sum(d["known_weight"] * (d["score"] or 0) for d in dimensions) / coverage, 2)
        if sufficient
        else None
    )
    return {
        "rules_version": rules["version"],
        "rules_revision": rules["revision"],
        "score": score,
        "coverage_percent": coverage,
        "sufficient_evidence": sufficient,
        "dimensions": dimensions,
        "provisional": True,
        "limitations": [
            "Matches are based on business-provided information. Verify partner details before entering commercial agreements.",
            "Only derived compatibility is disclosed; private assessment answers remain private.",
            "Previous cross-border experience is not required. Agree trade logistics before proceeding.",
        ],
    }
