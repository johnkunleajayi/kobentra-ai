"""Explicit discovery projection, separate from unrestricted tenant CRUD queries."""

from sqlalchemy import select

from ..models import BusinessProfile, MarketPreference


def profiles(db, source_id, published_ids):
    return list(
        db.scalars(
            select(BusinessProfile)
            .where(
                BusinessProfile.organization_id.in_(published_ids),
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
