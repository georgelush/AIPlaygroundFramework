"""
Lab 19 — Deploy Agent

Demonstrates how to expose agents as a REST API and connect them to external
workflow tools like n8n:
- Status report: lists all registered agents with type and description
- Health check: verifies the server and LLM proxy are reachable
- Info: returns framework metadata — endpoints, agent count, server port
- n8n integration: how to call this API from an HTTP Request node in n8n

Pattern: processor — takes a command string, returns a structured report.
New concepts: REST introspection, server registry, VS Code port forwarding, n8n HTTP Request.
"""

import httpx
from src.config import LLM_PROXY, LLM_API_KEY
from src.registry import AGENTS, META

AGENT_NAME = "Deploy Agent"
AGENT_TYPE = "processor"
AGENT_DESCRIPTION = "Reports server status, health, and registered agents. Shows how to expose the framework as a REST API callable from n8n."

trace_log: list[dict] = []

SERVER_PORT = 8080

COMMANDS = """Available commands:
  status  — list all registered agents with type and description
  health  — check if server and LLM proxy are reachable
  info    — framework metadata, endpoints, agent count
"""

def _cmd_status() -> str:
    """List all registered agents with type and description."""
    lines = [f"REGISTERED AGENTS — {len(AGENTS)} total\n"]
    for name, meta in META.items():
        lines.append("─" * 44)
        lines.append(f"  {name}")
        lines.append(f"  type:  {meta['type']}")
        lines.append(f"  desc:  {meta['description']}")
    lines.append("─" * 44)
    return "```\n" + "\n".join(lines) + "\n```"

def _cmd_health() -> str:
    """Check if the LLM proxy is reachable."""
    lines = ["HEALTH CHECK\n"]

    try:
        base = LLM_PROXY.rstrip("/").replace("/v1", "")
        response = httpx.get(base + "/health/liveliness", timeout=5.0)
        if response.status_code < 400:
            lines.append("  llm_proxy      = ok")
        else:
            lines.append(f"  llm_proxy      = FAIL  (status {response.status_code})")
    except Exception as e:
        lines.append(f"  llm_proxy      = FAIL  ({str(e)[:60]})")

    agent_count = len(AGENTS)
    if agent_count > 0:
        lines.append(f"  registry       = ok  ({agent_count} agents loaded)")
    else:
        lines.append("  registry       = FAIL  (no agents loaded)")

    lines.append("")
    return "```\n" + "\n".join(lines) + "\n```"

def _cmd_info() -> str:
    """Return framework metadata — endpoints, agent count, server port."""
    agent_types: dict[str, int] = {}
    for meta in META.values():
        t = meta["type"]
        agent_types[t] = agent_types.get(t, 0) + 1

    type_summary = "  ".join(f"{t}={count}" for t, count in agent_types.items())

    lines = [
        "FRAMEWORK INFO\n",
        f"  server_port    = {SERVER_PORT}",
        f"  agents_loaded  = {len(AGENTS)}",
        f"  agent_types    = {type_summary}",
        "",
        "  ENDPOINTS",
        "  ─────────────────────────────────────",
        "  GET  /health",
        "  GET  /agents",
        "  GET  /agents/{name}",
        "  POST /agents/{name}/runs   ← n8n calls this",
        "  GET  /agents/{name}/trace",
        "",
        "  N8N INTEGRATION",
        "  ─────────────────────────────────────",
        "  1. python server.py",
        "  2. VS Code → Ports → Forward 8080",
        "  3. Copy the public URL",
        "  4. n8n → HTTP Request node",
        "     Method: POST",
        "     URL:    <public_url>/agents/{agent_name}/runs",
        '     Body:   {"payload": "your message"}',
    ]

    return "```\n" + "\n".join(lines) + "\n```"

def run_agent(payload) -> str:
    trace_log.clear()

    command = str(payload).strip().lower() if payload else ""

    trace_log.append({
        "type": "node_exec",
        "label": "Deploy Agent",
        "from": "user",
        "to": "agent",
        "arrow": "->",
        "content": f"command: {command}",
    })

    if command == "status":
        result = _cmd_status()
    elif command == "health":
        result = _cmd_health()
    elif command == "info":
        result = _cmd_info()
    else:
        result = f"Unknown command: '{command}'\n\n{COMMANDS}"

    trace_log.append({
        "type": "llm_response",
        "label": "Result",
        "from": "agent",
        "to": "user",
        "arrow": "->",
        "content": command,
    })

    return result
