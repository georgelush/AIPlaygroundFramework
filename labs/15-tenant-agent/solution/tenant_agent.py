"""
Lab 15 — Multi-Tenant Agent

Demonstrates multi-tenancy patterns for production LLM agents:
- Budget isolation per user: each tenant has a token quota that cannot be exceeded
- thread_id namespacing: conversations are isolated per user (user_id:session_id)
- Quota enforcement: requests are blocked before reaching the LLM if quota is exceeded

In a real system, budgets would be stored in a database (PostgreSQL, Redis).
Here we use an in-memory dict to focus on the pattern, not the infrastructure.
"""

import json
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from typing import TypedDict

from src.config import LLM_MODEL, LLM_PROXY, LLM_API_KEY, langfuse_handler

AGENT_NAME = "Multi-Tenant Agent"
AGENT_TYPE = "chat"
AGENT_DESCRIPTION = "Demonstrates budget isolation, thread_id namespacing, and quota enforcement for multi-tenant LLM agents."

trace_log: list[dict] = []

SYSTEM_PROMPT = """
You are Multi-Tenant Agent — the 15th agent in the LangGraph learning series.
Your purpose: demonstrate how to build LLM agents that serve multiple isolated users, each with their own budget and conversation history.
Concepts you teach: budget isolation, thread_id namespacing, quota enforcement, tenant-aware design.
If asked who you are or why you exist — explain exactly this.
Only answer questions related to multi-tenancy patterns for AI agents, LangGraph, or the Agentic AI Playground framework.
If the user asks about their quota or budget — you may answer based on context provided.
If the user asks about anything else — politely decline and redirect them to the topics above.
"""

# --- Tenant storage (in-memory — replace with Redis/PostgreSQL in production) ---
DEFAULT_BUDGET = 5000  # tokens per user

_tenant_budgets: dict[str, int] = {}   # user_id -> tokens used


def get_tokens_used(user_id: str) -> int:
    """Returns how many tokens the user has consumed so far."""
    return _tenant_budgets.get(user_id, 0)


def update_tokens_used(user_id: str, tokens: int) -> None:
    """Adds tokens to the user's consumption counter."""
    _tenant_budgets[user_id] = _tenant_budgets.get(user_id, 0) + tokens


def is_within_budget(user_id: str) -> bool:
    """Returns True if the user has not exceeded their token budget."""
    return get_tokens_used(user_id) < DEFAULT_BUDGET


def make_thread_id(user_id: str, session_id: str) -> str:
    """Creates a namespaced thread_id: user_id:session_id."""
    return f"{user_id}:{session_id}"


# --- State ---
class State(TypedDict):
    messages: list
    user_id: str
    session_id: str
    quota_error: str | None


# --- LLM ---
llm = ChatOpenAI(
    model=LLM_MODEL,
    base_url=LLM_PROXY,
    api_key=LLM_API_KEY,
    temperature=0.7,
)


# --- Nodes ---
def node_check_quota(state: State) -> dict:
    """Checks if the user has remaining budget before calling the LLM."""
    used = get_tokens_used(state["user_id"])
    trace_log.append({
        "type": "node_exec",
        "label": "Quota Check",
        "from": "user",
        "to": "quota_checker",
        "arrow": "->",
        "content": f"User: {state['user_id']} | Used: {used}/{DEFAULT_BUDGET} tokens",
    })

    if not is_within_budget(state["user_id"]):
        return {"quota_error": f"Quota exceeded for user '{state['user_id']}'. Used: {used}/{DEFAULT_BUDGET} tokens."}

    return {"quota_error": None}


def node_quota_exceeded(state: State) -> dict:
    """Returns quota error message — LLM is never called."""
    trace_log.append({
        "type": "node_exec",
        "label": "Quota Exceeded",
        "from": "quota_checker",
        "to": "user",
        "arrow": "->",
        "content": state["quota_error"],
    })
    return {"messages": [{"role": "assistant", "content": state["quota_error"]}]}


def node_llm(state: State) -> dict:
    """Calls the LLM with tenant context injected into the message."""
    used = get_tokens_used(state["user_id"])
    context_prefix = f"[User: {state['user_id']} | Budget used: {used}/{DEFAULT_BUDGET} tokens]\n"

    trace_log.append({
        "type": "node_exec",
        "label": "LLM",
        "from": "quota_checker",
        "to": "llm",
        "arrow": "->",
        "content": context_prefix + state["messages"][-1] if state["messages"] else context_prefix,
    })

    user_message = state["messages"][0] if state["messages"] else ""
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=context_prefix + str(user_message)),
    ]

    response = llm.invoke(messages, config={"callbacks": [langfuse_handler]})

    # Estimate token usage: ~1 token per 4 characters
    estimated_tokens = len(response.content) // 4
    update_tokens_used(state["user_id"], estimated_tokens)

    trace_log.append({
        "type": "llm_response",
        "label": "LLM",
        "from": "llm",
        "to": "user",
        "arrow": "->",
        "content": response.content[:200],
    })

    return {"messages": [response]}


# --- Graph ---
def route_after_quota(state: State) -> str:
    """Routes to quota_exceeded if budget is exhausted, else to LLM."""
    if state["quota_error"]:
        return "quota_exceeded"
    return "llm"


def build_graph():
    g = StateGraph(State)

    g.add_node("check_quota", node_check_quota)
    g.add_node("quota_exceeded", node_quota_exceeded)
    g.add_node("llm", node_llm)

    g.add_edge(START, "check_quota")
    g.add_conditional_edges("check_quota", route_after_quota)
    g.add_edge("llm", END)
    g.add_edge("quota_exceeded", END)

    return g.compile(checkpointer=MemorySaver())


_graph = build_graph()


# --- Entry point ---
def run_agent(payload) -> str:
    trace_log.clear()

    if isinstance(payload, dict):
        user_input = payload.get("message", "")
        user_id = payload.get("user_id", "anonymous")
        session_id = payload.get("session_id", "default")
    else:
        try:
            data = json.loads(str(payload))
            user_input = data.get("message", str(payload))
            user_id = data.get("user_id", "anonymous")
            session_id = data.get("session_id", "default")
        except (json.JSONDecodeError, AttributeError):
            user_input = str(payload)
            user_id = "anonymous"
            session_id = "default"

    thread_id = make_thread_id(user_id, session_id)

    trace_log.append({
        "type": "node_exec",
        "label": "Thread",
        "from": "user",
        "to": "graph",
        "arrow": "->",
        "content": f"thread_id={thread_id} | user_id={user_id} | session_id={session_id}",
    })

    result = _graph.invoke(
        {
            "messages": [user_input],
            "user_id": user_id,
            "session_id": session_id,
            "quota_error": None,
        },
        config={"configurable": {"thread_id": thread_id}},
    )

    last = result["messages"][-1]
    content = last.content if hasattr(last, "content") else str(last.get("content", ""))
    return content or ""
