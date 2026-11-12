"""Explicit discovery projection, separate from unrestricted tenant CRUD queries."""

from sqlalchemy import select

from ..admin.deletion.models import DeletionOperation
from ..admin.models import BusinessAdministration
from ..models import BusinessProfile, MarketPreference
from ..qualification.evidence import eligible_query
from .features import build


def profiles(db, source_id, published_ids=None):
    return list(
        db.scalars(
            select(BusinessProfile)
            .outerjoin(
                BusinessAdministration,
                BusinessAdministration.organization_id == BusinessProfile.organization_id,
            )
            .where(
                BusinessProfile.organization_id.in_(eligible_query_ids()),
                (
                    BusinessAdministration.access.is_(None)
                    | (BusinessAdministration.access == "active")
                ),
                BusinessProfile.organization_id.not_in(select(DeletionOperation.organization_id)),
                BusinessProfile.organization_id != source_id,
            )
            .order_by(BusinessProfile.organization_id)
        )
    )


def inputs(db, profile):
    prefs = list(
        db.scalars(
            select(MarketPreference).where(
                MarketPreference.organization_id == profile.organization_id
            )
        )
    )
    return {
        "sector": profile.sector,
        "country": profile.country,
        "preferences": [{"country": p.country, "partner_type": p.partner_type} for p in prefs],
    }


def eligible_query_ids():
    from ..qualification.models import AssessmentEvidence

    return eligible_query(select(BusinessProfile.organization_id)).with_only_columns(
        AssessmentEvidence.organization_id
    )


def batch_inputs(db, profiles):
    from ..qualification.models import AssessmentEvidence

    ids = [p.organization_id for p in profiles]
    preferences = {i: [] for i in ids}
    evidence = {i: [] for i in ids}
    for pref in db.scalars(
        select(MarketPreference).where(MarketPreference.organization_id.in_(ids))
    ):
        preferences[pref.organization_id].append(
            {"country": pref.country, "partner_type": pref.partner_type}
        )
    for row in db.scalars(eligible_query(ids).order_by(AssessmentEvidence.id)):
        evidence[row.organization_id].append(row)
    return {
        p.organization_id: build(p, preferences[p.organization_id], evidence[p.organization_id])
        for p in profiles
    }
