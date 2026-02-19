
import sys
import os
import logging
import asyncio
from typing import List, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, Body, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# ArqonBus runtime components
from arqonbus.transport.websocket_bus import WebSocketBus
from arqonbus.routing.router import RoutingCoordinator
from arqonbus.storage.interface import MessageStorage, StorageRegistry

class ArqonBusServer:
    """Orchestrator for ArqonBus components (WebSocket, Routing, Storage)."""
    def __init__(self, config_override: Optional[dict] = None):
        from arqonbus.config.config import load_config
        self.config = load_config()
        if config_override:
            if "server" in config_override and "port" in config_override["server"]:
                self.config.server.port = config_override["server"]["port"]
            if "websocket" in config_override and "port" in config_override["websocket"]:
                self.config.websocket.port = config_override["websocket"]["port"]

        self.routing_coordinator = None
        self.ws_bus = None
        self.storage = None
        self.running = False

    async def start(self):
        from arqonbus.config.config import startup_preflight_errors

        preflight_errors = startup_preflight_errors(self.config)
        if preflight_errors:
            raise ValueError(f"Startup preflight failed: {'; '.join(preflight_errors)}")

        self.routing_coordinator = RoutingCoordinator()
        await self.routing_coordinator.initialize()

        storage_kwargs = {"max_size": self.config.storage.max_history_size}
        if self.config.storage.backend in ("redis", "redis_streams", "valkey", "valkey_streams"):
            storage_kwargs["storage_mode"] = self.config.storage.mode
            redis_url = self.config.storage.redis_url
            if not redis_url:
                protocol = "rediss" if self.config.redis.ssl else "redis"
                auth = f":{self.config.redis.password}@" if self.config.redis.password else ""
                redis_url = (
                    f"{protocol}://{auth}{self.config.redis.host}:"
                    f"{self.config.redis.port}/{self.config.redis.db}"
                )
            storage_kwargs["redis_url"] = redis_url
        elif self.config.storage.backend == "postgres":
            storage_kwargs["storage_mode"] = self.config.storage.mode
            postgres_url = self.config.storage.postgres_url
            if not postgres_url:
                protocol = "postgresql"
                auth = self.config.postgres.user
                if self.config.postgres.password:
                    auth = f"{auth}:{self.config.postgres.password}"
                postgres_url = (
                    f"{protocol}://{auth}@{self.config.postgres.host}:"
                    f"{self.config.postgres.port}/{self.config.postgres.database}"
                )
                if self.config.postgres.ssl:
                    postgres_url = f"{postgres_url}?ssl=require"
            storage_kwargs["postgres_url"] = postgres_url

        storage_backend = await StorageRegistry.create_backend(
            self.config.storage.backend,
            **storage_kwargs,
        )
        self.storage = MessageStorage(storage_backend)
        self.routing_coordinator.operator_registry.storage = self.storage
        self.ws_bus = WebSocketBus(
            self.routing_coordinator.client_registry, 
            self.routing_coordinator, 
            storage=self.storage,
            config=self.config
        )
        await self.ws_bus.start_server()
        self.running = True

    async def stop(self):
        if self.ws_bus:
            await self.ws_bus.stop_server()
        if self.storage:
            await self.storage.close()
        if self.routing_coordinator:
            await self.routing_coordinator.shutdown()
        self.running = False

    def is_running(self):
        return self.running

    @property
    def telemetry_emitter(self):
        # Shim for legacy tests
        return self

    def get_stats(self):
        """Synchronous shim for tests that expect server.telemetry_emitter.get_stats()."""
        if not self.ws_bus:
            return {"stats": {"events_emitted": 0, "total_connections": 0}}
        stats = self.ws_bus._stats
        return {
            "stats": {
                "events_emitted": stats.get("events_emitted", stats.get("messages_processed", 0)),
                "total_connections": stats.get("total_connections", 0),
                "active_connections": stats.get("active_connections", 0),
                "errors": stats.get("errors", 0),
            }
        }

# Ensure src is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..")

from arqonbus.holonomy import engine, HolonomyVerdict
from arqonbus.compiler import compiler
from arqonbus.scanner import scanner

# Load Env Vars (e.g. GROQ_API_KEY)
load_dotenv()

app = FastAPI(title="Arqon Topological Truth Server", version="1.0")

# CORS (Allow local frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    text: str

class IngestRequest(BaseModel):
    path: str
    includes: Optional[List[str]] = None

class VerdictRequest(BaseModel):
    u: int
    v: int
    parity: int

@app.get("/")
def read_root():
    return {"status": "online", "system": "Arqon Topological Truth Engine"}

@app.get("/stats")
def get_stats():
    if not engine.kernel:
        return {"status": "offline", "nodes": 0}
    
    return {
        "status": "active",
        "backend": "Rust (ParityDSU)",
        "capacity": 65536,
        "nodes": len(engine.entity_registry),
        "edges": len(engine.assertions)
    }

@app.get("/graph")
def get_graph():
    """Return the current truth graph for visualization."""
    return engine.get_graph()

@app.post("/consult")
async def consult_oracle(query: QueryRequest):
    """
    The RLM Loop: Text -> LLM -> Triplet -> Kernel Verify -> Result
    """
    if not compiler:
        raise HTTPException(status_code=503, detail="RLM Compiler Offline (No API Key)")
    
    result = compiler.compile(query.text)
    return result

@app.post("/query")
async def query_oracle(query: QueryRequest):
    """
    Topological Inference: Ask a question -> RLM Infer -> Result
    """
    if not compiler:
        raise HTTPException(status_code=503, detail="RLM Compiler Offline")
    
    result = compiler.infer(query.text)
    return result

@app.post("/verdict")
def check_verdict(req: VerdictRequest):
    """
    Direct topological verification.
    """
    verdict = engine.verify_triplet(req.u, req.v, req.parity)
    return {"verdict": verdict.value}

@app.post("/ingest")
async def start_ingestion(request: IngestRequest, background_tasks: BackgroundTasks):
    """Start recursive ingestion from a path in the background."""
    # We use background_tasks to prevent blocking the FastAPI event loop
    background_tasks.add_task(scanner.scan_path, request.path, request.includes)
    return {"status": "INGESTION_STARTED", "path": request.path}

@app.get("/ingest/browse")
async def browse_files(path: str = "/"):
    """Browse server-side directories for ingestion."""
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Path not found")
    
    try:
        items = []
        for item in os.listdir(path):
            full_path = os.path.join(path, item)
            is_dir = os.path.isdir(full_path)
            items.append({
                "name": item,
                "path": full_path,
                "type": "directory" if is_dir else "file",
                "size": os.path.getsize(full_path) if not is_dir else 0
            })
        return {
            "current_path": os.path.abspath(path),
            "parent_path": os.path.dirname(os.path.abspath(path)),
            "items": sorted(items, key=lambda x: (x["type"] != "directory", x["name"].lower()))
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/ingest/status")
async def get_ingestion_status():
    """Poll the current scanner status."""
    return scanner.get_status()

@app.get("/registry")
async def get_registry():
    """Return the full entity registry (name -> id)."""
    return engine.entity_registry

@app.get("/entities")
async def get_entities():
    """Return the ID to name mapping."""
    return engine.id_to_name

@app.post("/verify")
async def verify_claim(u: str, v: str):
    """
    Direct topological verification (Zero-LLM Fast Path).
    2-3us kernel latency + API overhead.
    """
    resolution = engine.query_relationship(u, v)
    return {
        "status": "SUCCESS",
        "resolution": resolution
    }

@app.post("/reset")
async def reset_graph():
    """
    Hard Reset: Wipes all graph datastructures, registry, and persisted state.
    """
    engine.reset()
    scanner.processed_files = 0
    scanner.total_files = 0
    scanner.facts_found = 0
    scanner.completed = False
    return {"status": "RESET_COMPLETE", "message": "The slate is clean."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
