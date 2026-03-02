"""Pydantic schemas for AuditTrail resource (read-only)."""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, Any

from pydantic import BaseModel


class AuditAction(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    EXPORT = "export"
    IMPORT = "import"
    APPROVE = "approve"
    REJECT = "reject"


class AuditTrailResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    user_email: Optional[str] = None
    user_name: Optional[str] = None
    action: AuditAction
    resource_type: str
    resource_id: Optional[uuid.UUID] = None
    resource_name: Optional[str] = None
    changes: Optional[dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: datetime
    metadata: Optional[dict] = None
    model_config = {"from_attributes": True}


class AuditTrailListResponse(BaseModel):
    items: list[AuditTrailResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
