from __future__ import annotations

import uuid

from pydantic import BaseModel


class CustomerCreate(BaseModel):
    name: str

class CustomerResponse(BaseModel):
    id: uuid.UUID
    name: str

    model_config = {"from_attributes": True}

