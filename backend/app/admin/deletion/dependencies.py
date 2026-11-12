from sqlalchemy import delete, func, select

from ...assessments.models import BusinessAssessment
from ...models import (
    Base,
    BusinessEvent,
    BusinessProfile,
    IntroductionRequest,
    MarketPreference,
    MatchExplanation,
    Membership,
    Opportunity,
)
from ...qualification.models import AssessmentEvidence
from ..models import BusinessAdministration

PURGE_ORDER = (
    AssessmentEvidence,
    MatchExplanation,
    IntroductionRequest,
    Opportunity,
    BusinessEvent,
    MarketPreference,
    BusinessAssessment,
    Membership,
    BusinessProfile,
    BusinessAdministration,
)


def dependencies(db, business_id):
    allowed = {m.__tablename__ for m in PURGE_ORDER} | {
        "administrative_decisions",
        "business_deletions",
    }
    if any(
        "organization_id" in table.c and table.name not in allowed
        for table in Base.metadata.tables.values()
    ):
        raise ValueError("Unreviewed organization dependency")
    return {
        model.__tablename__: db.scalar(
            select(func.count()).select_from(model).where(model.organization_id == business_id)
        )
        for model in PURGE_ORDER
    }


def purge(db, business_id):
    dependencies(db, business_id)  # Future models fail closed until deletion behavior is reviewed.
    for model in PURGE_ORDER:
        db.execute(delete(model).where(model.organization_id == business_id))
