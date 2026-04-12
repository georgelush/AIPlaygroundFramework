"""
src/graphs/hr_graph.py — StateGraph for the HR Assistant agent (Lab 20).
Compiled once at module level — imported and reused by src/agents/capstone_agent.py.

Requires Redis for HITL checkpointing:
    docker compose up -d redis
"""
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.redis import RedisSaver
from langchain_core.messages import ToolMessage

from src.config import REDIS_URL
from src.nodes.hr_nodes import node_llm, node_approve
from src.tools.hr_tools import TOOLS


def route_post_tools(state: MessagesState) -> str:
    """After tools execute: route to HR approval gate only if submit_vacation_request succeeded.
    If the tool returned a validation error (starts with 'Error:'), route back to LLM."""
    for msg in reversed(state["messages"]):
        if isinstance(msg, ToolMessage):
            if msg.name == "submit_vacation_request" and not msg.content.startswith("Error:"):
                return "approve"
            break
    return "llm"


def build_graph():
    """Build and compile the HR Assistant graph with Redis checkpointer."""
    tool_node = ToolNode(TOOLS)

    _cm = RedisSaver.from_conn_string(REDIS_URL)
    checkpointer = _cm.__enter__()
    checkpointer.setup()

    g = StateGraph(MessagesState)
    g.add_node("llm", node_llm)
    g.add_node("tools", tool_node)
    g.add_node("approve", node_approve)

    g.add_edge(START, "llm")
    g.add_conditional_edges("llm", tools_condition)
    g.add_conditional_edges("tools", route_post_tools, {"approve": "approve", "llm": "llm"})
    g.add_edge("approve", END)

    return g.compile(checkpointer=checkpointer)


# Compiled once — reused on every run_agent() call.
# Redis must be running: docker compose up -d redis
graph = build_graph()
