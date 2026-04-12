"""
Lab 17 — Approval Agent

Demonstrates approval workflow patterns for production LLM agents:
- Sensitive operation detection: certain actions require explicit approval before execution
- Manager sign-off simulation: high-risk requests are escalated and held pending approval
- Escalation path: the agent explains what approval is needed and how to proceed

This agent combines patterns from Lab 09 (HITL) and Lab 16 (Auth):
- Like Lab 09: execution is blocked until approval is granted
- Like Lab 16: risk level is determined by action type, not just user role

In a real system, approval requests would be sent via email/Teams/Slack to a manager.
Here we simulate approval with an in-memory pending queue and a special 'approve:' command.
"""

import uuid
from datetime import datetime, timezone
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from typing import TypedDict

from src.config import LLM_MODEL, LLM_PROXY, LLM_API_KEY, langfuse_handler

AGENT_NAME = "Approval Agent"
AGENT_TYPE = "chat"
AGENT_DESCRIPTION = "Demonstrates approval workflows — sensitive operations require manager sign-off before execution."

trace_log: list[dict] = []

# Pending approval queue: request_id -> {user_id, action, message, timestamp}
_pending_approvals: dict[str, dict] = {}

SYSTEM_PROMPT = """
You are Approval Agent — the seventeenth agent in the LangGraph learning series.
Your purpose: demonstrate approval workflows — some operations are sensitive and require
manager sign-off before they can be executed.
Concepts you teach: approval queues, pending state, escalation paths, risk classification.
If asked who you are or why you exist — explain exactly this.

Sensitive operations that require approval (examples):
- Delete or purge data ("delete all users", "drop table", "purge logs")
- Financial actions ("transfer money", "refund", "charge")
- Deployments to production ("deploy to prod", "release", "push to production")
- Access changes ("grant admin", "reset all passwords")

For everything else — answer normally as a helpful assistant.
"""

llm = ChatOpenAI(
    model=LLM_MODEL,
    base_url=LLM_PROXY,
    api_key=LLM_API_KEY,
    temperature=0,
)

class State(TypedDict):
    user_input: str
    is_sensitive: bool
    request_id: str
    answer: str


def node_classify(state: State) -> dict:
    trace_log.append({
        "type": "node_exec",
        "label": "Classify",
        "from": "user",
        "to": "classifier",
        "arrow": "->",
        "content": state["user_input"][:200],
    })

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=(
            f"Classify this request. Reply with exactly one word: SENSITIVE or SAFE.\n\n"
            f"Request: {state['user_input']}"
        )),
    ]

    response = llm.invoke(messages, config={"callbacks": [langfuse_handler]})
    verdict = response.content.strip().upper()
    is_sensitive = "SENSITIVE" in verdict

    trace_log.append({
        "type": "llm_response",
        "label": "Classify Result",
        "from": "classifier",
        "to": "router",
        "arrow": "->",
        "content": verdict,
    })

    return {"is_sensitive": is_sensitive}


def node_queue(state: State) -> dict:
    request_id = str(uuid.uuid4())[:8]
    _pending_approvals[request_id] = {
        "user_input": state["user_input"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    trace_log.append({
        "type": "tool_call",
        "label": "Queue",
        "from": "agent",
        "to": "approval_queue",
        "arrow": "->",
        "content": f"request_id={request_id} | {state['user_input'][:100]}",
    })

    answer = (
        f"This action requires manager approval before it can be executed.\n\n"
        f"Request ID: **{request_id}**\n\n"
        f"To approve, send:\n```\napprove:{request_id}\n```\n"
        f"To reject, send:\n```\nreject:{request_id}\n```"
    )

    return {"request_id": request_id, "answer": answer}

def node_respond(state: State) -> dict:
    trace_log.append({
        "type": "node_exec",
        "label": "Respond",
        "from": "llm",
        "to": "user",
        "arrow": "->",
        "content": state["user_input"][:200],
    })

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=state["user_input"]),
    ]

    response = llm.invoke(messages, config={"callbacks": [langfuse_handler]})

    trace_log.append({
        "type": "llm_response",
        "label": "LLM",
        "from": "llm",
        "to": "user",
        "arrow": "->",
        "content": response.content[:200],
    })

    return {"answer": response.content or ""}

def node_check_approval(state: State) -> dict:
    user_input = state["user_input"].strip()

    if user_input.startswith("approve:"):
        request_id = user_input.split(":", 1)[1].strip()
        if request_id in _pending_approvals:
            approved_request = _pending_approvals.pop(request_id)
            trace_log.append({
                "type": "tool_result",
                "label": "Approved",
                "from": "manager",
                "to": "agent",
                "arrow": "->",
                "content": f"request_id={request_id} | {approved_request['user_input'][:100]}",
            })
            return {
                "answer": (
                    f"Request **{request_id}** approved.\n\n"
                    f"Executing: _{approved_request['user_input']}_\n\n"
                    f"[SIMULATED] Operation completed successfully."
                )
            }
        return {"answer": f"Request ID `{request_id}` not found or already processed."}

    if user_input.startswith("reject:"):
        request_id = user_input.split(":", 1)[1].strip()
        if request_id in _pending_approvals:
            _pending_approvals.pop(request_id)
            trace_log.append({
                "type": "tool_result",
                "label": "Rejected",
                "from": "manager",
                "to": "agent",
                "arrow": "->",
                "content": f"request_id={request_id} | rejected by manager",
            })
            return {"answer": f"Request **{request_id}** rejected. Operation cancelled."}
        return {"answer": f"Request ID `{request_id}` not found or already processed."}

    return {"answer": ""}

def route_input(state: State) -> str:
    user_input = state["user_input"].strip()
    if user_input.startswith("approve:") or user_input.startswith("reject:"):
        return "check_approval"
    if state["is_sensitive"]:
        return "queue"
    return "respond"


def build_graph():
    g = StateGraph(State)

    g.add_node("classify", node_classify)
    g.add_node("check_approval", node_check_approval)
    g.add_node("queue", node_queue)
    g.add_node("respond", node_respond)

    g.add_edge(START, "classify")
    g.add_conditional_edges("classify", route_input)
    g.add_edge("queue", END)
    g.add_edge("respond", END)
    g.add_edge("check_approval", END)

    return g.compile()


_graph = build_graph()

def run_agent(payload) -> str:
    trace_log.clear()

    if isinstance(payload, dict):
        user_input = payload.get("message", "")
    else:
        try:
            import json
            data = json.loads(str(payload))
            user_input = data.get("message", str(payload))
        except (json.JSONDecodeError, AttributeError):
            user_input = str(payload)

    result = _graph.invoke({
        "user_input": user_input,
        "is_sensitive": False,
        "request_id": "",
        "answer": "",
    })

    return result["answer"] or ""