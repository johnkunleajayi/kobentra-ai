"""Bounded cross-tenant projections. Called only by authorized administrative routes."""

from sqlalchemy import func, or_, select

from ..assessments.models import BusinessAssessment
from ..models import BusinessProfile, Membership, Organization, User
from ..qualification.models import AssessmentEvidence
from .eligibility import statuses
from .models import BusinessAdministration


def count(db, model):
    return db.scalar(select(func.count()).select_from(model))


def summary(db):
    return {
        "users": count(db, User),
        "businesses": count(db, BusinessProfile),
        "workspaces": count(db, Organization),
        "assessment_statuses": dict(
            db.execute(
                select(BusinessAssessment.status, func.count()).group_by(BusinessAssessment.status)
            ).all()
        ),
        "qualification": {
            "self_reported_snapshots": count(db, AssessmentEvidence),
            "independent_verification": "platform_owner_decisions",
            "verified_business_identities": db.scalar(
                select(func.count())
                .select_from(BusinessAdministration)
                .where(BusinessAdministration.identity == "verified")
            ),
        },
    }


def search(statement, columns, query):
    if query:
        value = "%" + query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        statement = statement.where(or_(*(c.ilike(value, escape="\\") for c in columns)))
    return statement


def page_rows(db, statement, page, page_size):
    total = db.scalar(select(func.count()).select_from(statement.subquery()))
    return list(db.scalars(statement.offset((page - 1) * page_size).limit(page_size))), total


def users(db, query, page, page_size):
    rows, total = page_rows(
        db, search(select(User).order_by(User.id), [User.email], query), page, page_size
    )
    associations = {u.id: [] for u in rows}
    if rows:
        for member, org in db.execute(
            select(Membership, Organization)
            .join(Organization)
            .where(Membership.user_id.in_(associations))
            .order_by(Organization.id)
        ):
            associations[member.user_id].append(
                {"business_id": org.id, "name": org.name, "role": member.role}
            )
    return {
        "items": [
            {"id": u.id, "email": u.email, "created_at": None, "businesses": associations[u.id]}
            for u in rows
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def owners(db, ids):
    result = {i: [] for i in ids}
    if ids:
        for member, user in db.execute(
            select(Membership, User)
            .join(User)
            .where(Membership.organization_id.in_(ids), Membership.role == "owner")
            .order_by(User.id)
        ):
            result[member.organization_id].append({"id": user.id, "email": user.email})
    return result


def profile_summary(profile, owner_list):
    return {
        "id": profile.organization_id,
        "name": profile.name,
        "country": profile.country,
        "industry": profile.sector,
        "owners": owner_list,
        "registered_at": None,
        "business_status": "not_recorded",
    }


def businesses(db, query, page, page_size):
    rows, total = page_rows(
        db,
        search(
            select(BusinessProfile).order_by(BusinessProfile.organization_id),
            [BusinessProfile.name, BusinessProfile.country, BusinessProfile.sector],
            query,
        ),
        page,
        page_size,
    )
    owned = owners(db, [r.organization_id for r in rows])
    states = statuses(db, [r.organization_id for r in rows])
    return {
        "items": [
            {
                **profile_summary(r, owned[r.organization_id]),
                "administration": states.get(
                    r.organization_id,
                    dict(approval="pending", identity="unverified", access="active", version=0),
                ),
            }
            for r in rows
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }
