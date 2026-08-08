"""WebSocket hub: broadcast state messages to all connected browsers.

Message envelope (PRD section 7):
    { "type": ..., "ts": ISO8601, "data": {...} }
"""
import asyncio
import json
from datetime import datetime, timezone
from typing import Any

from fastapi import WebSocket


class WsHub:
    def __init__(self) -> None:
        self._clients: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._clients.add(ws)

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            self._clients.discard(ws)

    async def broadcast(self, type_: str, data: dict[str, Any]) -> None:
        message = json.dumps(
            {"type": type_, "ts": datetime.now(timezone.utc).isoformat(), "data": data}
        )
        async with self._lock:
            clients = list(self._clients)
        for ws in clients:
            try:
                await ws.send_text(message)
            except Exception:
                await self.disconnect(ws)


hub = WsHub()
