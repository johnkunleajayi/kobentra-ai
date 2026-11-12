from .features import text

ALIASES = {
    "distributors or resellers": "distributors",
    "suppliers or manufacturers": "manufacturers",
    "buyers or customers": "buyers",
    "strategic partners": "strategic",
}


def interests(item, target_country, rules):
    raw = [
        p["partner_type"] for p in item["preferences"] if text(p["country"]) == text(target_country)
    ]
    raw += item.get("assessment", {}).get("partnerships", [])
    aliases = {text(k): v for k, v in rules["intent_aliases"].items()} | ALIASES
    return {aliases[text(v)] for v in raw if text(v) in aliases}


def industry(source, partner, complementary, rules):
    def words(item):
        assessment = item.get("assessment", {})
        return (
            set(text(item["sector"]).split())
            | set(text(" ".join(assessment.get("industry", []))).split())
            | set(assessment.get("capability_words", ()))
        )

    food = {"food", "foods", "beverage", "beverages", "snacks", "snack"}
    a, b = words(source), words(partner)
    if a & food and b & food:
        return (
            "compatible",
            "Both declare food/product relevance; capabilities remain self-reported.",
            1,
        )
    if text(source["sector"]) and text(source["sector"]) == text(partner["sector"]):
        return (
            "compatible",
            "Same declared industry; product and capability detail needs agreement.",
            rules["industry_known_fraction"],
        )
    if complementary and (
        (a & food and b & {"distribution", "wholesale", "distributor"})
        or (b & food and a & {"distribution", "wholesale", "distributor"})
    ):
        return (
            "compatible",
            "Food production and distribution interests complement each other; confirm product scope.",
            0.5,
        )
    return "unknown", "Industry labels alone do not establish product or capability fit.", 0


def operations(source, partner, rules):
    a, b = source.get("assessment", {}), partner.get("assessment", {})
    bands = rules["capacity_bands"]
    values = [bands.get(text(" ".join(item.get("capacity", [])))) for item in (a, b)]
    if all(values) and values[0] == values[1]:
        return (
            "compatible",
            "Comparable declared capacity bands; agree order volumes and logistics before trading.",
            0.5,
        )
    return (
        "unknown",
        "Operational capacity/order-volume fit needs clarification. Company age and previous cross-border experience do not gate discovery.",
        0,
    )


def timing(source, partner, rules):
    windows = rules["timeline_windows"]
    a, b = [
        windows.get(text(" ".join(item.get("assessment", {}).get("timeline", []))))
        for item in (source, partner)
    ]
    if a and b and max(a[0], b[0]) <= min(a[1], b[1]):
        return "compatible", "Declared readiness windows overlap; agree a specific start date.", 0.5
    return (
        "unknown",
        "Agree a partnership start date; missing or different windows are not an automatic rejection.",
        0,
    )
