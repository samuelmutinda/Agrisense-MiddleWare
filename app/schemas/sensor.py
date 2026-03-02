from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SensorUplinkEvent(BaseModel):
    event: str
    timestamp: Optional[datetime]
    tenant: Optional[str]
    application: Optional[str]
    device_name: Optional[str]
    dev_eui: Optional[str]
    dev_addr: Optional[str]
    f_cnt: Optional[int]
    confirmed: Optional[bool]
    f_port: Optional[int]
    data_base64: Optional[str]
    decoded_object: Optional[Dict[str, Any]]
    rx_info: List[Dict[str, Any]] = Field(default_factory=list)
    tx_info: Optional[Dict[str, Any]]
    region: Optional[str]

