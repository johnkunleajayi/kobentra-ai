from fastapi import APIRouter, Request, Response

from ..business.routes import Database, Identity
from ..workspace.identifiers import RecordID
from .service import matches

router = APIRouter(prefix="/api/businesses/{business_id}", tags=["Partner matching"])


@router.get("/matches")
def potential_matches(
    business_id: RecordID, principal: Identity, db: Database, request: Request, response: Response
):
    response.headers["Cache-Control"] = "no-store"
    return matches(db, principal, business_id)
