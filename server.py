"""
server.py - FastAPI REST server for agent execution.
Usage: python server.py
Port:  8080

Endpoints:
    GET  /agents                       → list all agents with metadata
    GET  /agents/{agent_name}          → get agent details
    POST /agents/{agent_name}/runs     → execute an agent (LangGraph Platform standard)
    GET  /agents/{agent_name}/trace    → last execution trace
    GET  /health                       → health check
"""
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any

from src.registry import AGENTS, TRACES, META

# ── App ────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Agent Server",
    description="REST API for LangGraph agents. Callable from n8n, Power Automate, etc.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Schemas ────────────────────────────────────────────────────────────────────

class RunRequest(BaseModel):
    payload: Any  # string for chat agents, dict for processor/pipeline agents


class RunResponse(BaseModel):
    agent: str
    result: Any
    trace_steps: int


# ── Endpoints ──────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "agents_loaded": len(AGENTS)}


@app.get("/agents")
def list_agents():
    """Returns all registered agents with metadata."""
    return {
        "agents": [
            {
                "name": name,
                "type": META[name]["type"],
                "description": META[name]["description"],
                "module": META[name]["module"],
            }
            for name in AGENTS
        ]
    }


@app.get("/agents/{agent_name}")
def get_agent(agent_name: str):
    """Returns details for a specific agent."""
    if agent_name not in AGENTS:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found.")
    return {
        "name": agent_name,
        **META[agent_name],
    }


@app.post("/agents/{agent_name}/runs", response_model=RunResponse)
def run_agent(agent_name: str, body: RunRequest):
    """
    Execute an agent with the given payload.
    For 'chat' agents, payload is a string.
    For other agents, payload is a dict.

    Example n8n (HTTP Request node):
        POST /agents/Hello Agent/runs
        Body: { "payload": "What is LangGraph?" }
    """
    if agent_name not in AGENTS:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found.")
    try:
        result = AGENTS[agent_name](body.payload)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    trace = TRACES.get(agent_name) or []
    return RunResponse(agent=agent_name, result=result, trace_steps=len(trace))


@app.get("/agents/{agent_name}/trace")
def get_trace(agent_name: str):
    """Returns the last execution trace for an agent."""
    if agent_name not in AGENTS:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found.")
    trace = TRACES.get(agent_name) or []
    return {"agent": agent_name, "steps": len(trace), "trace": trace}


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("[Server] Ready at http://127.0.0.1:8080")
    print("[Server] Docs  at http://127.0.0.1:8080/docs")
    uvicorn.run(app, host="0.0.0.0", port=8080)
