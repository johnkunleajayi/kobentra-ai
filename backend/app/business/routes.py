from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from ..db_session import get_db
from ..security import Principal, require_principal
from .repository import list_businesses
from .schemas import BusinessList, BusinessRegistration, BusinessSummary
from .service import register_business

router = APIRouter(prefix="/api/businesses", tags=["Businesses"])
Identity = Annotated[Principal, Depends(require_principal)]
Database = Annotated[Session, Depends(get_db)]


def require_write_origin(request: Request) -> None:
    # Same cookie-auth CSRF policy as logout; fail closed for missing/null origins.
    if request.headers.get("origin") not in request.app.state.settings.cors_origins:
        raise HTTPException(403, "Invalid request origin")
    if request.headers.get("content-type", "").split(";", 1)[0].strip() != "application/json":
        raise HTTPException(415, "JSON required")


@router.post("", response_model=BusinessSummary, dependencies=[Depends(require_write_origin)])
def create_business(
    data: BusinessRegistration, principal: Identity, db: Database, response: Response
):
    result, created = register_business(db, principal.user_id, data)
    response.status_code = 201 if created else 200
    response.headers["Cache-Control"] = "no-store"
    return result


@router.get("", response_model=BusinessList)
def my_businesses(principal: Identity, db: Database, response: Response):
    response.headers["Cache-Control"] = "no-store"
    return BusinessList(businesses=list_businesses(db, principal.user_id))
