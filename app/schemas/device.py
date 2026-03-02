from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

class DeviceCreate(BaseModel):
    name: str
    cold_storage_unit_id: Optional[uuid.UUID] = None

class DeviceUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None
    cold_storage_unit_id: Optional[uuid.UUID] = None

class DeviceResponse(BaseModel):
    id: uuid.UUID
    dev_eui: str
    app_key: str
    name: str
    is_active: bool
    created_at: datetime
    cold_storage_unit_id: Optional[uuid.UUID] = None

    model_config = ConfigDict(from_attributes=True)
