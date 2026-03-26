"""
Notification delivery endpoints.

Provides an authenticated API surface over the existing multi-channel
notification service so frontend clients do not call Firebase Cloud Functions
or Firestore directly.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.api import deps
from app.core.security import AuthContext
from app.services.notification_service import (
    NotificationChannel,
    NotificationPriority,
    NotificationRequest,
    NotificationResult,
    send_notification,
    send_push_fcm,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


class SendNotificationRequest(BaseModel):
    recipient_id: str
    channel: NotificationChannel
    title: str
    body: str
    priority: NotificationPriority = NotificationPriority.NORMAL
    recipient_email: Optional[str] = None
    recipient_phone: Optional[str] = None
    recipient_fcm_token: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class SendTopicNotificationRequest(BaseModel):
    title: str
    body: str
    priority: NotificationPriority = NotificationPriority.NORMAL
    metadata: Optional[Dict[str, Any]] = None


@router.post("/send", response_model=NotificationResult, summary="Send a notification")
async def send_notification_endpoint(
    request: SendNotificationRequest,
    auth: AuthContext = Depends(deps.get_auth_context),
):
    service_request = NotificationRequest(
        recipient_id=request.recipient_id,
        channel=request.channel,
        title=request.title,
        body=request.body,
        priority=request.priority,
        recipient_email=request.recipient_email,
        recipient_phone=request.recipient_phone,
        recipient_fcm_token=request.recipient_fcm_token,
        metadata=request.metadata,
    )
    return await send_notification(service_request)


@router.post("/topics/{topic}", response_model=NotificationResult, summary="Send a push notification to a topic")
async def send_topic_notification_endpoint(
    topic: str,
    request: SendTopicNotificationRequest,
    auth: AuthContext = Depends(deps.get_auth_context),
):
    return await send_push_fcm(
        fcm_token=f"/topics/{topic}",
        title=request.title,
        body=request.body,
        data=request.metadata,
    )


# ---------------------------------------------------------------------------
# Notification History
# ---------------------------------------------------------------------------

class NotificationHistoryEntry(BaseModel):
    id: str
    title: str
    body: str
    channel: str
    priority: str
    category: Optional[str] = None
    status: str
    sent_at: str
    read_at: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class NotificationHistoryResponse(BaseModel):
    items: List[NotificationHistoryEntry]
    total: int


@router.get("/history", response_model=NotificationHistoryResponse, summary="Get notification history")
async def get_notification_history(
    limit: int = Query(50, ge=1, le=200),
    category: Optional[str] = Query(None),
    unread_only: bool = Query(False),
    auth: AuthContext = Depends(deps.get_auth_context),
):
    """Return notification history for the authenticated user.

    Currently returns an empty list because the underlying notification log
    table hasn't been provisioned yet. Once the table exists, this endpoint
    will query it with the supplied filters.
    """
    # TODO: Wire to notification_log table once schema is provisioned
    return NotificationHistoryResponse(items=[], total=0)
