"""
Event Broadcaster for Real-time SSE (Server-Sent Events) streaming.
"""
from __future__ import annotations

import asyncio
import json
from typing import AsyncGenerator, Dict, Any, List

class EventBroadcaster:
    def __init__(self):
        self._subscribers: List[asyncio.Queue] = []

    async def subscribe(self) -> AsyncGenerator[str, None]:
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers.append(queue)
        try:
            while True:
                data = await queue.get()
                yield f"data: {json.dumps(data)}\n\n"
        except asyncio.CancelledError:
            self._subscribers.remove(queue)

    async def broadcast(self, event_type: str, payload: Dict[str, Any]) -> None:
        message = {"type": event_type, "payload": payload}
        for q in list(self._subscribers):
            await q.put(message)

events = EventBroadcaster()
