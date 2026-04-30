from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

# Import adapters so @register decorators fire at startup
import backend.factory  # noqa: F401

from backend.api.routes import registry, datasets, experiments
from backend.api.websocket import run_status_ws

app = FastAPI(title="RAG Benchmark API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(registry.router)
app.include_router(datasets.router)
app.include_router(experiments.router)


@app.websocket("/ws/runs/{run_id}")
async def websocket_run(websocket: WebSocket, run_id: str):
    await run_status_ws(websocket, run_id)


@app.get("/health")
def health():
    return {"status": "ok"}
