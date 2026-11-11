from sqlalchemy.orm import Session

from ..security import Principal, authorize
from ..workspace.transactions import tenant_write
from .repository import list_preferences, replace_preferences
from .schemas import PreferenceInput, PreferencesInput


def read(db: Session, principal: Principal, business_id: str) -> PreferencesInput:
    authorize(db, principal, business_id)
    return PreferencesInput(
        preferences=[
            PreferenceInput(country=p.country, partner_type=p.partner_type)
            for p in list_preferences(db, business_id)
        ]
    )


def save(db: Session, principal: Principal, business_id: str, data: PreferencesInput):
    with tenant_write(db, principal, business_id):
        replace_preferences(db, business_id, data.preferences)
        result = PreferencesInput(
            preferences=[
                PreferenceInput(country=p.country, partner_type=p.partner_type)
                for p in list_preferences(db, business_id)
            ]
        )
    return result
