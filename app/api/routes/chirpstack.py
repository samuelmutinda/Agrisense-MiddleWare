"""
ChirpStack webhook ingestion endpoint.

This endpoint receives HTTP webhooks from ChirpStack and forwards them
to WebSocket subscribers. It validates the bearer token to ensure
requests are from the authorized ChirpStack instance.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.api import deps
from app.core.config import get_settings
from app.services import chirpstack_service

router = APIRouter(prefix="/integrations/chirpstack", tags=["chirpstack"])

# Named security scheme for ChirpStack webhook authentication
# This is separate from user authentication and uses a different token format
# Using HTTPBearer ensures Swagger shows "Authorization: Bearer <token>" format
chirpstack_webhook_security = HTTPBearer(
    scheme_name="ChirpStackWebhookToken",
    description="Bearer token for ChirpStack webhook authentication. This is a system-to-system token, not a user token.",
    auto_error=False,  # We'll handle errors in verify_chirpstack_token
)


async def verify_chirpstack_token(
    credentials: HTTPAuthorizationCredentials = Security(chirpstack_webhook_security),
) -> None:
    """
    Verify that the bearer token matches the configured ChirpStack webhook token.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing ChirpStack webhook token",
        )
    
    settings = get_settings()
    if not settings.chirpstack_webhook_token:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ChirpStack webhook token not configured",
        )
    
    if credentials.credentials != settings.chirpstack_webhook_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid ChirpStack webhook token",
        )

@router.post("/events")
async def chirpstack_events(
    request: Request,
    session=Depends(deps.get_system_db),
    # Explicitly declare security scheme in function signature for OpenAPI/Swagger
    # This ensures Swagger shows "Authorization: Bearer <token>" format
    credentials: HTTPAuthorizationCredentials = Security(chirpstack_webhook_security),
):
    """
    Receive ChirpStack webhook events and relay them to WebSocket subscribers.

    This endpoint:
    - Validates bearer token authentication (system-to-system, not user-based)
    - Accepts raw ChirpStack payloads
    - Extracts event type from query parameter (defaults to "unknown")
    - Normalizes and filters events
    - Emits to authorized WebSocket clients

    **Authentication**: Uses system-level bearer token validation, not user authentication.
    ChirpStack is a system integration, not a user, so it does not have user credentials.

    **Database Access**: Uses system-level database session without tenant context.
    Tenant is resolved from the ChirpStack payload itself.

    Requires valid bearer token in Authorization header.
    Query parameter 'event' specifies the event type (e.g., "up", "join", "ack").
    """
    # Validate the token
    await verify_chirpstack_token(credentials)
    
    # Handle empty body gracefully (Swagger sends -d '' instead of -d '{}')
    body = await request.body()
    if body:
        try:
            import json
            payload = json.loads(body)
        except Exception:
            # If JSON parsing fails, default to empty dict
            payload = {}
    else:
        payload = {}
    
    event_type = request.query_params.get("event", "unknown")
    return await chirpstack_service.process_uplink_event(session, payload, event_type)
