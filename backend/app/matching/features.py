"""Internal derived features. Never serialize these inputs to another tenant."""

import re
from html import unescape

from ..qualification.scoring_inputs import collect


def text(value):
    return (
        " ".join(re.findall(r"[a-z0-9]+", unescape(value).casefold()))
        if isinstance(value, str)
        else ""
    )


def choices(value):
    return [v["value"] for v in value] if isinstance(value, list) else []


def build(profile, preferences, snapshots):
    values, conflicts, issues = collect(snapshots)
    eligible = len(values) == 10 and not conflicts and not issues and bool(preferences)
    countries = choices(values.get("primary_country"))
    profile_conflict = countries and text(countries[0]) != text(profile.country)
    # Identity text mismatch is disclosed for the owner by readiness, not an independent verification gate.
    return {
        "sector": profile.sector,
        "country": profile.country,
        "preferences": preferences,
        "eligible": bool(eligible),
        "conflicts": ["geography"] if profile_conflict else [],
        "assessment": {
            "industry": choices(values.get("industry")),
            "partnerships": choices(values.get("partnership_types")),
            "markets": choices(values.get("markets_served")),
            "capacity": choices(values.get("operational_capacity")),
            "timeline": choices(values.get("readiness_timeline")),
            "capability_words": set(text(values.get("capabilities")).split()),
            "years": values.get("years_operating"),
            "cross_border": values.get("cross_border_experience"),
        },
    }
