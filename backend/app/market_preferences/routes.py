from fastapi import APIRouter, Depends, Response

from ..business.routes import Database, Identity, require_write_origin
from ..workspace.identifiers import RecordID
from . import service
from .schemas import PreferencesInput

router = APIRouter(
    prefix="/api/businesses/{business_id}/market-preferences", tags=["Market preferences"]
)


@router.get("", response_model=PreferencesInput)
def get_preferences(business_id: RecordID, principal: Identity, db: Database, response: Response):
    response.headers["Cache-Control"] = "no-store"
    return service.read(db, principal, business_id)


@router.put("", response_model=PreferencesInput, dependencies=[Depends(require_write_origin)])
def put_preferences(
    business_id: RecordID,
    data: PreferencesInput,
    principal: Identity,
    db: Database,
    response: Response,
):
    response.headers["Cache-Control"] = "no-store"
    return service.save(db, principal, business_id, data)
