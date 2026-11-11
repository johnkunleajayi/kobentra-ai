"""Authentication and tenant-level authorization."""

from dataclasses import dataclass

from fastapi import HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from .auth_sessions import get_active_session
from .models import Membership


@dataclass(frozen=True)
class Principal:
    user_id: str


def require_principal(request: Request) -> Principal:
    """Resolve the authenticated user from a server-side session."""

    settings = request.app.state.settings
    engine = request.app.state.database_engine

    token = request.cookies.get(settings.session_cookie_name)

    if not token:
        raise HTTPException(401, detail="Authentication required")

    with Session(engine) as db:
        active_session = get_active_session(db, token)

        if active_session is None:
            raise HTTPException(401, detail="Authentication required")

        return Principal(user_id=active_session.user_id)


def authorize(
    session: Session,
    principal: Principal,
    organization_id: str,
    write: bool = False,
) -> Membership:
    member = session.get(
        Membership,
        (principal.user_id, organization_id),
    )

    if member is None or member.role not in {
        "owner",
        "admin",
        "member",
    }:
        raise HTTPException(403, detail="Access denied")

    if write and member.role not in {"owner", "admin"}:
        raise HTTPException(403, detail="Access denied")

    from .admin.eligibility import require_operational
    require_operational(session, organization_id)

    return member


def scoped_list(
    session: Session,
    model,
    principal: Principal,
    organization_id: str,
):
    authorize(session, principal, organization_id)

    return list(session.scalars(select(model).where(model.organization_id == organization_id)))


def scoped_get(
    session: Session,
    model,
    principal: Principal,
    organization_id: str,
    record_id: str,
):
    authorize(session, principal, organization_id)

    row = session.scalar(
        select(model).where(
            model.organization_id == organization_id,
            model.id == record_id,
        )
    )

    if row is None:
        raise HTTPException(404, detail="Record not found")

    return row
