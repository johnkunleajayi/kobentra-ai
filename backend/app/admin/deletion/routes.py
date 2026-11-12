from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy.exc import SQLAlchemyError

from ...business.routes import Database, require_write_origin
from ...salesforce.client import SalesforceError
from ...workspace.identifiers import RecordID
from ..authorization import require_platform_owner
from . import service
from .preview import preview
from .schemas import DeleteConfirmation

Owner = Annotated[object, Depends(require_platform_owner)]
router = APIRouter(
    prefix="/api/admin/businesses/{business_id}/deletion", tags=["Business deletion"]
)


class RetryInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operation_id: UUID


@router.get("/preview")
def deletion_preview(business_id: RecordID, owner: Owner, db: Database, request: Request):
    try:
        result = preview(db, business_id, request.app.state.salesforce_client)
        if result["salesforce_target"]:
            result["salesforce_target"] = {
                k: v for k, v in result["salesforce_target"].items() if k != "binding_hash"
            }
        result["salesforce_deletion_enabled"] = (
            request.app.state.settings.salesforce_business_deletion_enabled
        )
        return result
    except (SalesforceError, ValueError, KeyError, TypeError, AttributeError):
        raise HTTPException(503, "Deletion linkage or dependency review unavailable") from None


@router.get("")
def status(business_id: RecordID, owner: Owner, db: Database):
    return service.operation_status(db, business_id)


@router.post("")
def confirm(
    business_id: RecordID, data: DeleteConfirmation, owner: Owner, db: Database, request: Request
):
    require_write_origin(request)
    try:
        op_id = service.initiate(
            db,
            owner,
            request.app.state.settings,
            business_id,
            data,
            request.app.state.salesforce_client,
        )
        service.advance(
            db,
            owner,
            request.app.state.settings,
            business_id,
            op_id,
            request.app.state.salesforce_client,
        )
        return service.operation_status(db, business_id)
    except (SQLAlchemyError, SalesforceError, ValueError, KeyError, TypeError, AttributeError):
        db.rollback()
        raise HTTPException(
            503, "Deletion not confirmed; retrieve operation status before retrying"
        ) from None


@router.post("/retry")
def retry(business_id: RecordID, data: RetryInput, owner: Owner, db: Database, request: Request):
    require_write_origin(request)
    try:
        service.advance(
            db,
            owner,
            request.app.state.settings,
            business_id,
            str(data.operation_id),
            request.app.state.salesforce_client,
        )
        return service.operation_status(db, business_id)
    except (SQLAlchemyError, ValueError, KeyError, TypeError, AttributeError):
        db.rollback()
        raise HTTPException(503, "Deletion not confirmed; inspect status and retry") from None
