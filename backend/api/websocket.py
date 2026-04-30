from __future__ import annotations
import asyncio
import json
from fastapi import WebSocket, WebSocketDisconnect
from backend.api.routes.experiments import _active_runs


async def run_status_ws(websocket: WebSocket, run_id: str):
    await websocket.accept()
    try:
        while True:
            run = _active_runs.get(run_id)
            if run is None:
                await websocket.send_json({"error": f"Run '{run_id}' not found"})
                break
            await websocket.send_json(run.model_dump())
            if run.status in ("done", "error"):
                break
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass
    finally:
        await websocket.close()
