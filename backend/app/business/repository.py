from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import BusinessProfile, Membership, Organization, User
from .schemas import BusinessRegistration, BusinessSummary


def lock_registrant(db: Session, user_id: str) -> User | None:
    return db.scalar(select(User).where(User.id == user_id).with_for_update())


def list_businesses(db: Session, user_id: str) -> list[BusinessSummary]:
    rows = db.execute(
        select(BusinessProfile, Membership.role)
        .join(Membership, Membership.organization_id == BusinessProfile.organization_id)
        .where(Membership.user_id == user_id, Membership.role.in_(["owner", "admin", "member"]))
        .order_by(BusinessProfile.name, BusinessProfile.organization_id)
    )
    return [summarize(profile, role) for profile, role in rows]


def existing_registration(db: Session, user_id: str, data: BusinessRegistration):
    return db.scalar(
        select(BusinessProfile)
        .join(Membership, Membership.organization_id == BusinessProfile.organization_id)
        .where(
            Membership.user_id == user_id,
            Membership.role == "owner",
            BusinessProfile.name == data.name,
            BusinessProfile.sector == data.sector,
            BusinessProfile.country == data.country,
            BusinessProfile.goal == data.goal,
        )
        .order_by(BusinessProfile.organization_id)
    )


def create_business(db: Session, user_id: str, data: BusinessRegistration) -> BusinessProfile:
    organization = Organization(name=data.name)
    db.add(organization)
    db.flush()
    profile = BusinessProfile(organization_id=organization.id, **data.model_dump())
    db.add_all(
        [profile, Membership(user_id=user_id, organization_id=organization.id, role="owner")]
    )
    db.flush()
    return profile


def summarize(profile: BusinessProfile, role: str) -> BusinessSummary:
    return BusinessSummary(
        organization_id=profile.organization_id,
        profile_id=profile.id,
        name=profile.name,
        sector=profile.sector,
        country=profile.country,
        goal=profile.goal,
        role=role,
    )
