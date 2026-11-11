from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from ..business.routes import Database, require_write_origin
from ..workspace.identifiers import RecordID
from .authorization import require_platform_owner
from .history import history
from .mutation_schemas import ProfileDecision, StatusDecision
from .mutations import mutate

Owner = Annotated[object, Depends(require_platform_owner)]
router = APIRouter(prefix="/api/admin/businesses/{business_id}", tags=["Business administration"])


@router.post("/decisions")
def decide(
    business_id: RecordID, data: StatusDecision, owner: Owner, db: Database, request: Request
):
    require_write_origin(request)
    return mutate(db, owner, request.app.state.settings, business_id, data)


@router.put("/profile")
def edit(
    business_id: RecordID, data: ProfileDecision, owner: Owner, db: Database, request: Request
):
    require_write_origin(request)
    return mutate(db, owner, request.app.state.settings, business_id, data)


@router.get("/history")
def decisions(
    business_id: RecordID,
    owner: Owner,
    db: Database,
    page: Annotated[int, Query(ge=1, le=100000)] = 1,
):
    return history(db, business_id, page)
