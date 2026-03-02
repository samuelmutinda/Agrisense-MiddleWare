from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from fastapi import WebSocket

from app.core.config import get_settings


@dataclass
class WsConnection:
    websocket: WebSocket
    tenant_id: str
    customer_ids: List[str] = field(default_factory=list)
    device_ids: List[str] = field(default_factory=list)


class WebSocketManager:
    def __init__(self) -> None:
        self._connections: Dict[str, List[WsConnection]] = {}
        self._lock = asyncio.Lock()
        self._settings = get_settings()

    async def connect(self, websocket: WebSocket, connection: WsConnection) -> None:
        await websocket.accept()
        async with self._lock:
            tenant_list = self._connections.setdefault(connection.tenant_id, [])
            tenant_list.append(connection)

            if len(tenant_list) > self._settings.websocket_max_connections:
                tenant_list.pop(0)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            for tenant_id, conns in list(self._connections.items()):
                self._connections[tenant_id] = [
                    c for c in conns if c.websocket != websocket
                ]
                if not self._connections[tenant_id]:
                    self._connections.pop(tenant_id, None)

    async def broadcast(
        self,
        tenant_id: str,
        payload: dict,
        customer_id: Optional[str] = None,
        device_id: Optional[str] = None,
    ) -> None:
        async with self._lock:
            recipients = list(self._connections.get(tenant_id, []))

        to_remove: List[WebSocket] = []
        for conn in recipients:
            if customer_id and conn.customer_ids and customer_id not in conn.customer_ids:
                continue
            if device_id and conn.device_ids and device_id not in conn.device_ids:
                continue
            try:
                await conn.websocket.send_json(payload)
            except Exception:
                to_remove.append(conn.websocket)

        for ws in to_remove:
            await self.disconnect(ws)


manager = WebSocketManager()

