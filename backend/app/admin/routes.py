from typing import Annotated

from fastapi import APIRouter, Depends, Query

from ..business.routes import Database
from ..workspace.identifiers import RecordID
from . import repository
from .authorization import require_platform_owner
from .details import business_detail

router = APIRouter(
    prefix="/api/admin", tags=["Administration"], dependencies=[Depends(require_platform_owner)]
)
Page = Annotated[int, Query(ge=1, le=100000)]
Size = Annotated[int, Query(ge=1, le=100)]
Search = Annotated[str, Query(max_length=100)]


@router.get("/dashboard")
def dashboard(db: Database):
    return repository.summary(db)


@router.get("/users")
def users(db: Database, q: Search = "", page: Page = 1, page_size: Size = 20):
    return repository.users(db, q.strip(), page, page_size)


@router.get("/businesses")
def businesses(db: Database, q: Search = "", page: Page = 1, page_size: Size = 20):
    return repository.businesses(db, q.strip(), page, page_size)


@router.get("/businesses/{business_id}")
def detail(business_id: RecordID, db: Database):
    return business_detail(db, business_id)
