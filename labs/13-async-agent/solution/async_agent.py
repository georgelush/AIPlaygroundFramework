"""
Agent 13 — Async Agent
Pattern: Non-blocking background task with job_id polling.
Teaches: asyncio, ainvoke(), threading.Thread, Redis job store, polling pattern.

Instead of waiting for the LLM to finish (blocking), this agent:
1. Returns a job_id immediately (< 100ms)
2. Runs the LLM call in a background thread (with simulated 15s delay)
3. Stores the result in Redis when done
4. Returns the result when polled with "job:<id>"

Flow — Submit:
  user text -> node_start: generate job_id -> start background thread
            -> return {"job_id": ..., "status": "running"}

Flow — Poll:
  "job:<id>" -> node_poll: check Redis
             -> return {"status": "running"} or {"status": "done", "result": ...}

Production note:
  In n8n or any webhook-capable system, replace polling entirely:
  Agent calls httpx.AsyncClient().post(callback_url, json=result) when done.
  The webhook receiver gets the result automatically — no polling needed.
"""

import asyncio
import json
import threading
import time
import uuid

import redis
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from typing import TypedDict

from src.config import LLM_API_KEY, LLM_MODEL, LLM_PROXY, langfuse_handler

AGENT_NAME = "Async Agent"
AGENT_TYPE = "processor"
AGENT_DESCRIPTION = (
    "Demonstrates non-blocking async execution. "
    "Submit a task — get a job_id immediately. "
    "Poll with 'job:<id>' to check status and retrieve the result."
)

trace_log: list[dict] = []

redis_client = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)
JOB_TTL = 3600  # jobs expire after 1 hour

SYSTEM_PROMPT = """
You are Async Agent — the 13th agent in the LangGraph learning series.
Your purpose: demonstrate non-blocking async execution with job_id polling.
Concepts you teach: threading, background tasks, job_id pattern, polling, webhook callbacks.
If asked who you are or why you exist — explain exactly this.
Only answer questions related to this agent, its concepts, LangGraph, or the AI Playground Framework we are building.
If the user asks about anything else — politely decline and redirect them to the topics above.
"""

# ── State ──────────────────────────────────────────────────────────────────────

class State(TypedDict):
    user_input: str
    job_id: str
    status: str
    result: str

# ── LLM ───────────────────────────────────────────────────────────────────────

llm = ChatOpenAI(
    model=LLM_MODEL,
    base_url=LLM_PROXY,
    api_key=LLM_API_KEY,
    temperature=0.7,
)

# ── Background worker (async) ──────────────────────────────────────────────────

async def _run_llm_async(job_id: str, user_input: str) -> None:
    """Async coroutine — uses ainvoke() to call LLM without blocking the event loop."""
    await asyncio.sleep(15)  # async sleep — yields control instead of blocking
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_input),
    ]
    # ainvoke() — async version of invoke() — must be awaited inside async def
    response = await llm.ainvoke(messages, config={"callbacks": [langfuse_handler]})
    result = response.content or ""
    redis_client.setex(job_id, JOB_TTL, json.dumps({"status": "done", "result": result}))


def _run_in_thread(job_id: str, user_input: str) -> None:
    """Thread entry point — creates a fresh event loop to run the async coroutine."""
    # asyncio.run() creates a NEW event loop for this thread and runs the coroutine
    # This is required because the main thread's event loop (Gradio/FastAPI) is already running
    asyncio.run(_run_llm_async(job_id, user_input))

# ── Nodes ──────────────────────────────────────────────────────────────────────

def node_start(state: State) -> dict:
    """Generates a job_id, stores initial status in Redis, starts background thread."""
    job_id = str(uuid.uuid4())
    redis_client.setex(job_id, JOB_TTL, json.dumps({"status": "running", "result": ""}))

    # Thread runs _run_in_thread → which calls asyncio.run() → which awaits ainvoke()
    thread = threading.Thread(target=_run_in_thread, args=(job_id, state["user_input"]), daemon=True)
    thread.start()

    trace_log.append({
        "type": "node_exec",
        "label": "START",
        "from": "user",
        "to": "node_start",
        "arrow": "->",
        "content": f"job_id={job_id} | ainvoke() started in background thread | input={state['user_input'][:80]}",
    })

    return {"job_id": job_id, "status": "running", "result": ""}


def node_poll(state: State) -> dict:
    """Checks Redis for the job result."""
    job_id = state["job_id"]
    raw = redis_client.get(job_id)

    if raw is None:
        trace_log.append({
            "type": "node_exec",
            "label": "POLL",
            "from": "user",
            "to": "node_poll",
            "arrow": "->",
            "content": f"job_id={job_id} | not found in Redis",
        })
        return {"status": "not_found", "result": ""}

    data = json.loads(raw)
    trace_log.append({
        "type": "node_exec",
        "label": "POLL",
        "from": "user",
        "to": "node_poll",
        "arrow": "->",
        "content": f"job_id={job_id} | status={data['status']} | result={data.get('result', '')[:80]}",
    })
    return {"status": data["status"], "result": data.get("result", "")}


def node_webhook_demo(state: State) -> dict:
    """Simulates a slow blocking task, then fires a webhook POST alert."""
    trace_log.append({
        "type": "node_exec",
        "label": "WEBHOOK",
        "from": "user",
        "to": "node_webhook_demo",
        "arrow": "->",
        "content": f"Task received: {state['user_input'][8:50]} | Simulating 5s processing...",
    })

    time.sleep(5)  # simulate slow work — blocking intentionally for demo

    trace_log.append({
        "type": "llm_response",
        "label": "WEBHOOK FIRED",
        "from": "node_webhook_demo",
        "to": "caller",
        "arrow": "->",
        "content": "POST request sent to callback URL — payload: {status: done, result: ...}",
    })

    return {
        "status": "done",
        "result": "Webhook activated — POST alert sent.",
    }

# ── Router ────────────────────────────────────────────────────────────────────

def route(state: State) -> str:
    """Routes based on input prefix: 'job:' → poll, 'webhook:' → webhook demo, else → start."""
    if state["user_input"].startswith("job:"):
        return "poll"
    if state["user_input"].startswith("webhook:"):
        return "webhook"
    return "start"

# ── Graph ──────────────────────────────────────────────────────────────────────

def build_graph():
    g = StateGraph(State)
    g.add_node("start", node_start)
    g.add_node("poll", node_poll)
    g.add_node("webhook", node_webhook_demo)
    g.add_conditional_edges(START, route)
    g.add_edge("start", END)
    g.add_edge("poll", END)
    g.add_edge("webhook", END)
    return g.compile()

_graph = build_graph()

# ── Entry point ───────────────────────────────────────────────────────────────

def run_agent(payload) -> str:
    trace_log.clear()
    user_input = str(payload).strip()

    if user_input.startswith("job:"):
        job_id = user_input[4:].strip()
        result = _graph.invoke({"user_input": user_input, "job_id": job_id, "status": "", "result": ""})
    else:
        result = _graph.invoke({"user_input": user_input, "job_id": "", "status": "", "result": ""})

    is_poll = user_input.startswith("job:")
    status = result.get("status", "")
    job_id = result.get("job_id", "")
    llm_result = result.get("result", "")

    if status == "running" and not is_poll:
        # first submit — job just started
        return (
            f"Job started — processing in background with `ainvoke()`.\n\n"
            f"**Job ID:** `{job_id}`\n\n"
            f"Poll for result with:\n```\njob:{job_id}\n```"
        )
    if status == "running" and is_poll:
        # poll while still in progress
        polled_id = user_input[4:].strip()
        return (
            f"Still processing... `ainvoke()` is running in background.\n\n"
            f"Poll again in a few seconds with:\n```\njob:{polled_id}\n```"
        )
    if status == "done":
        return llm_result or "Done — no result returned."
    if status == "not_found":
        return "Job not found in Redis — it may have expired (TTL: 1 hour) or the ID is incorrect."
    # webhook demo or unknown
    return llm_result or str(result)
