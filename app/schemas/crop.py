from __future__ import annotations

import uuid
from typing import Optional

from pydantic import BaseModel, Field


class CropCreate(BaseModel):
    name: str
    unit_of_measure: str = Field(..., description="Unit of measure for the crop (e.g., 'kg', 'bags', 'tons')")
    shelf_life_hrs: float = Field(..., gt=0, description="Shelf life in hours")
    storage_temp_celsius: float = Field(..., description="Storage temperature in degrees Celsius")
    crop_description: Optional[str] = Field(None, description="Description of the crop")


class CropResponse(BaseModel):
    id: uuid.UUID
    name: str
    unit_of_measure: str
    shelf_life_hrs: float
    storage_temp_celsius: float
    crop_description: Optional[str] = None

    model_config = {"from_attributes": True}

