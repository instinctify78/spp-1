"""In-memory token streaming registry.

Maps run_id -> asyncio.Queue so WebSocket handlers can receive tokens
published by inference threads via call_soon_threadsafe.

Sentinel value None signals end-of-stream.
"""

import asyncio
from typing import Any

_queues: dict[int, asyncio.Queue] = {}


def create_queue(run_id: int) -> asyncio.Queue:
    q: asyncio.Queue[Any] = asyncio.Queue()
    _queues[run_id] = q
    return q


def get_queue(run_id: int) -> asyncio.Queue | None:
    return _queues.get(run_id)


def remove_queue(run_id: int) -> None:
    _queues.pop(run_id, None)
