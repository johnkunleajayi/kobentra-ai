import logging
from contextlib import asynccontextmanager
from typing import Annotated
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware

from .assessments.native_routes import router as native_assessments_router
from .assessments.routes import router as assessments_router
from .auth_routes import router as auth_router
from .business.routes import router as business_router
from .config import Settings
from .database import database_engine
from .market_preferences.routes import router as preferences_router
from .opportunities.routes import router as opportunities_router
from .qualification.routes import router as qualification_router
from .salesforce.client import SalesforceClient
from .security import Principal, require_principal
from .workspace.routes import router as workspace_router

logger = logging.getLogger("kobentra")


@asynccontextmanager
async def lifespan(api):
    client = api.state.salesforce_client
    try:
        yield
    finally:
        client.close()
        if api.state.salesforce_client is not client:
            api.state.salesforce_client.close()


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    api = FastAPI(title="Kobentra API", version="0.1.0", lifespan=lifespan)
    api.state.settings = settings
    api.state.database_engine = database_engine(settings)
    api.state.salesforce_client = SalesforceClient(settings)
    # Temporary signed OAuth state storage.
    # Production must use HTTPS and secure cookies.
    if settings.oauth_session_secret:
        api.add_middleware(
            SessionMiddleware,
            secret_key=settings.oauth_session_secret.get_secret_value(),
            session_cookie="kobentra_oauth",
            max_age=600,
            same_site="lax",
            https_only=settings.google_redirect_uri.startswith("https://"),
        )
    api.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT"],
        allow_headers=["Content-Type"],
    )

    @api.middleware("http")
    async def request_id(request: Request, call_next):
        request.state.request_id = str(uuid4())
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    def error(request, status, code):
        return JSONResponse(
            status_code=status,
            content={
                "error": {
                    "code": code,
                    "request_id": getattr(request.state, "request_id", None),
                }
            },
        )

    @api.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: HTTPException):
        return error(
            request,
            exc.status_code,
            {
                401: "authentication_required",
                403: "access_denied",
                404: "not_found",
            }.get(exc.status_code, "request_failed"),
        )

    @api.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        # Do not return rejected input values or log bodies.
        return error(request, 422, "validation_failed")

    @api.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception):
        logger.error("request_failed request_id=%s", getattr(request.state, "request_id", None))
        return error(request, 500, "internal_error")

    @api.get("/api/health")
    def health():
        return {
            "status": "ok",
            "phase": 1,
            "database": "not_connected",
            "authentication": "not_configured",
            "salesforce": "not_connected",
            "eventspark": "planned",
        }

    @api.get("/api/workspace")
    def workspace(principal: Annotated[Principal, Depends(require_principal)]):
        raise HTTPException(503, detail="Workspace API is not implemented")

    if (
        settings.google_client_id
        and settings.google_client_secret
        and settings.oauth_session_secret
    ):
        api.include_router(auth_router)

    api.include_router(business_router)
    api.include_router(workspace_router)
    api.include_router(preferences_router)
    api.include_router(opportunities_router)
    api.include_router(assessments_router)
    api.include_router(native_assessments_router)
    api.include_router(qualification_router)
    return api


app = create_app()
