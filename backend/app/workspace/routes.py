from fastapi import APIRouter, HTTPException, Response
from sqlalchemy import select

from ..business.repository import summarize
from ..business.routes import Database, Identity
from ..business.schemas import BusinessSummary
from ..models import BusinessProfile
from ..security import authorize
from .identifiers import RecordID

router = APIRouter(prefix="/api/businesses", tags=["Workspace"])


@router.get("/{business_id}", response_model=BusinessSummary)
def workspace(business_id: RecordID, principal: Identity, db: Database, response: Response):
    member = authorize(db, principal, business_id)
    profile = db.scalar(
        select(BusinessProfile).where(BusinessProfile.organization_id == business_id)
    )
    if profile is None:
        raise HTTPException(404, "Business not found")
    response.headers["Cache-Control"] = "no-store"
    return summarize(profile, member.role)
