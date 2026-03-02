from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ORMModel(BaseModel):
    model_config = {"from_attributes": True}  # Pydantic v2 syntax (was orm_mode in v1)


class Timestamped(ORMModel):
    created_at: datetime = Field(default_factory=datetime.utcnow)

