from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import MarketPreference
from .schemas import PreferenceInput


def list_preferences(db: Session, organization_id: str) -> list[MarketPreference]:
    return list(
        db.scalars(
            select(MarketPreference)
            .where(MarketPreference.organization_id == organization_id)
            .order_by(MarketPreference.country, MarketPreference.partner_type)
        )
    )


def replace_preferences(db: Session, organization_id: str, values: list[PreferenceInput]):
    existing = {
        (row.country, row.partner_type): row for row in list_preferences(db, organization_id)
    }
    desired = {(value.country, value.partner_type) for value in values}
    for key, row in existing.items():
        if key not in desired:
            db.delete(row)
    for country, partner_type in desired - existing.keys():
        db.add(
            MarketPreference(
                organization_id=organization_id, country=country, partner_type=partner_type
            )
        )
    db.flush()
