from dataclasses import dataclass

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Membership


@dataclass(frozen=True)
class Principal:
    user_id: str
    # Future verified server-side identity, never a browser-provided identity header.


def require_principal() -> Principal:
    raise HTTPException(401, detail="Authentication is not configured")


def authorize(
    session: Session, principal: Principal, organization_id: str, write: bool = False
) -> Membership:
    member = session.get(Membership, (principal.user_id, organization_id))
    if member is None or member.role not in {"owner", "admin", "member"}:
        raise HTTPException(403, detail="Access denied")
    if write and member.role not in {"owner", "admin"}:
        raise HTTPException(403, detail="Access denied")
    return member


def scoped_list(session: Session, model, principal: Principal, organization_id: str):
    authorize(session, principal, organization_id)
    return list(session.scalars(select(model).where(model.organization_id == organization_id)))


def scoped_get(session: Session, model, principal: Principal, organization_id: str, record_id: str):
    authorize(session, principal, organization_id)
    row = session.scalar(
        select(model).where(model.organization_id == organization_id, model.id == record_id)
    )
    if row is None:
        raise HTTPException(404, detail="Record not found")
    return row
