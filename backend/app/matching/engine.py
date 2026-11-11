"""Score declared compatibility, never readiness or independent verification."""

import json
from pathlib import Path

RULES = json.loads(Path(__file__).with_name("rules.json").read_text(encoding="utf-8"))


def normalized(value):
    return " ".join(value.split()).casefold() if isinstance(value, str) else ""


def compare(source, partner, rules=None):
    """Inputs are profile fields and explicitly discovery-approved market preferences.

    No assessment text, scores, raw evidence, opportunities or contact details enter
    this engine. Conflicting dimensions must be unknown, never a favorable match.
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

    def intents(item, target_country):
        return {
            rules["intent_aliases"][normalized(p["partner_type"])]
            for p in item["preferences"]
            if normalized(p["partner_type"]) in rules["intent_aliases"]
            and normalized(p["country"]) == normalized(target_country)
        }

    a, b = intents(source, partner["country"]), intents(partner, source["country"])
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
    same_sector = normalized(source["sector"]) == normalized(partner["sector"])
    add(
        "industry_capability",
        "compatible" if same_sector and normalized(source["sector"]) else "unknown",
        "Same declared industry; capabilities remain unknown."
        if same_sector
        else "Different or missing industries do not establish capability fit or incompatibility.",
        rules["industry_known_fraction"],
    )
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
    add(
        "operations",
        "unknown",
        "No structured operational requirements or discovery-approved capacity evidence.",
    )
    add("timing", "unknown", "No structured shared partnership timing requirements.")
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
        "score": score,
        "coverage_percent": coverage,
        "sufficient_evidence": sufficient,
        "dimensions": dimensions,
        "provisional": True,
        "limitations": [
            "All disclosed business information is self-reported.",
            "Readiness and identity verification are separate from compatibility.",
            "Private assessments are not used for cross-tenant discovery.",
        ],
    }
