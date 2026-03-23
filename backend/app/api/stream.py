"""WebSocket endpoint for real-time token streaming."""

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

import app.streaming as streaming

router = APIRouter()


@router.websocket("/ws/runs/{run_id}")
async def stream_run(websocket: WebSocket, run_id: int):
    await websocket.accept()

    queue = streaming.get_queue(run_id)
    if queue is None:
        # Run already completed or doesn't exist — send done immediately
        await websocket.send_json({"type": "done"})
        await websocket.close()
        return

    try:
        while True:
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=60.0)
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "ping"})
                continue

            await websocket.send_json(msg)

            if msg.get("type") == "done":
                break

    except WebSocketDisconnect:
        pass
    finally:
        streaming.remove_queue(run_id)
        await websocket.close()
