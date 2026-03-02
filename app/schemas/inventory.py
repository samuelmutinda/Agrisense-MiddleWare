from __future__ import annotations

import uuid
from typing import List, Optional

from pydantic import BaseModel

class InventoryPosition(BaseModel):
    intake_id: uuid.UUID
    crop_id: uuid.UUID
    customer_id: uuid.UUID
    cold_storage_unit_id: Optional[uuid.UUID]
    quantity: int


class InventoryByStorage(BaseModel):
    cold_storage_unit_id: Optional[uuid.UUID]
    quantity: int


class InventorySummary(BaseModel):
    total_quantity: int
    by_storage: List[InventoryByStorage]

