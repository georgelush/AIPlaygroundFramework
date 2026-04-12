"""
Agent 0 — Ping Agent
Pattern: No LLM, no graph — static response only.
Purpose: Verify that Studio and server are running correctly.
Send any message — always replies: "Hello! All systems working fine."
"""

AGENT_NAME = "Ping Agent"
AGENT_TYPE = "chat"
AGENT_DESCRIPTION = "Health check agent — no LLM, no graph. Send any message to verify Studio and server are running correctly."

trace_log: list[dict] = []


def run_agent(payload: str) -> str:
    trace_log.clear()
    trace_log.append({
        "type": "node_exec",
        "label": "Ping",
        "from": "user",
        "to": "ping",
        "arrow": "->",
        "content": payload[:200],
        "fn": "run_agent",
    })
    trace_log.append({
        "type": "llm_response",
        "label": "Pong",
        "from": "ping",
        "to": "user",
        "arrow": "->",
        "content": "Hello! All systems working fine.",
        "fn": "run_agent",
    })
    return "Hello! All systems working fine."
