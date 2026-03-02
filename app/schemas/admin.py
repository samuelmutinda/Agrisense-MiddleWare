from __future__ import annotations

import uuid
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, ConfigDict


class TenantCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    chirpstack_application_id: Optional[uuid.UUID] = None
    chirpstack_device_profile_id: Optional[uuid.UUID] = None


class TenantUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    chirpstack_application_id: Optional[uuid.UUID] = None
    chirpstack_device_profile_id: Optional[uuid.UUID] = None


class TenantResponse(BaseModel):
    id: uuid.UUID
    name: str
    chirpstack_application_id: Optional[uuid.UUID] = None
    chirpstack_device_profile_id: Optional[uuid.UUID] = None

    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    tenant_id: uuid.UUID
    role_id: uuid.UUID
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8)  # Production standard: min 8 chars
    phone: str = Field(..., min_length=1)


class UserUpdate(BaseModel):
    role_id: Optional[uuid.UUID] = None
    first_name: Optional[str] = Field(None, min_length=1)
    last_name: Optional[str] = Field(None, min_length=1)
    phone: Optional[str] = Field(None, min_length=1)
    # email: Optional[EmailStr] = None # Add this if admins can change emails


class UserResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    role_id: uuid.UUID
    first_name: str
    last_name: str
    email: EmailStr # Changed to EmailStr for consistency
    phone: str

    model_config = ConfigDict(from_attributes=True)


class RoleResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)