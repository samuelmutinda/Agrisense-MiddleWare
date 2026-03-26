from __future__ import annotations

from contextlib import asynccontextmanager
import logging
import re

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import get_api_router
from app.core.bootstrap import run_sysadmin_bootstrap_if_configured
from app.core.config import get_settings
from app.services import chirpstack_client, influxdb_service
from app.core.security import decode_token
from app.db.base import Base
from app.db.session import engine
from app.ws.manager import WsConnection, manager

from sqlalchemy.exc import IntegrityError, DBAPIError

from app.core.exceptions import ChirpStackError

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    try:
        await run_sysadmin_bootstrap_if_configured()
    except Exception as e:
        logger.warning("Sysadmin bootstrap skipped: %s", e)

    yield

    await influxdb_service.close_client()
    await chirpstack_client.close_client()
    await engine.dispose()


settings = get_settings()
app = FastAPI(title=settings.app_name, lifespan=lifespan)


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    logger.warning(f"ValueError caught: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)}
    )


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    error_msg = str(exc.orig)
    detail = "Data integrity violation."

    if "is not present in table" in error_msg:
        match = re.search(r"Key \((.*?)\)=\(.*?\) is not present in table \"(.*?)\"", error_msg)
        if match:
            field, table = match.groups()
            detail = f"The provided {field} does not exist in the {table} records."
        else:
            detail = "Related record not found (foreign key violation)."

    elif "already exists" in error_msg:
        match = re.search(r"Key \((.*?)\)=\(.*?\) already exists", error_msg)
        if match:
            field = match.group(1)
            detail = f"A record with this {field} already exists."
        else:
            detail = "This record already exists (unique constraint violation)."

    elif "null value in column" in error_msg:
        match = re.search(r"column \"(.*?)\" of relation \"(.*?)\"", error_msg)
        if match:
            field, table = match.groups()
            detail = f"The field '{field}' is required for {table}."
        else:
            detail = "A required field is missing."

    else:
        logger.error(f"Unparsed Integrity Error: {error_msg}")
        detail = "Database constraint violation occurred."

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": detail}
    )

@app.exception_handler(DBAPIError)
async def database_error_handler(_request: Request, exc: DBAPIError):
    logger.critical(f"Database connection issue: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": "Database connection lost or timed out. Please try again later."}
    )


@app.exception_handler(ChirpStackError)
async def chirpstack_error_handler(_request: Request, exc: ChirpStackError):
    """ChirpStack errors category: relay ChirpStack API failures back to the user."""
    logger.warning(f"ChirpStack error: {exc.message}", exc_info=True)
    content = {"detail": exc.message, "chirpstack_error": True}
    if exc.body is not None:
        content["chirpstack"] = exc.body
    return JSONResponse(status_code=exc.status_code, content=content)


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {type(exc).__name__}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred"}
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin) for origin in settings.cors_origins_list] or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(get_api_router(), prefix=settings.api_prefix)


@app.websocket("/ws/tenant")
async def websocket_endpoint(websocket: WebSocket):
    token = websocket.query_params.get("token")
    try:
        auth = decode_token(token or "")
        if auth is None:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        connection = WsConnection(
            websocket=websocket,
            tenant_id=str(auth.tenant_id),
            customer_ids=[str(c) for c in auth.customer_ids],
            device_ids=[d for d in auth.device_ids],
        )

        await manager.connect(websocket, connection)

        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)