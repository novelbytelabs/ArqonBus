
import sys
import os
import logging
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Body, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

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
    """Start recursive ingestion from a path."""
    background_tasks.add_task(scanner.scan_path, request.path, request.includes)
    return {"status": "INGESTION_STARTED", "path": request.path}

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
