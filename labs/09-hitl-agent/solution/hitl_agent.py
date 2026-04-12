"""
Agent 9 — HITL Agent
Pattern: Human-in-the-Loop — interrupt() approval gate before sensitive actions.
Purpose: Pause graph execution and wait for human approval before proceeding.
Concepts: interrupt(), Command(resume=), get_state(), approval gate, SqliteSaver.
Send a sensitive request (e.g. "delete all files") — agent pauses and asks for approval.
Reply 'approve' or 'reject' to resume execution.
"""

import os
import sqlite3
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.types import interrupt, Command
from langgraph.checkpoint.sqlite import SqliteSaver
from src.config import LLM_MODEL, LLM_PROXY, LLM_API_KEY, langfuse_handler

AGENT_NAME = "HITL Agent"
AGENT_TYPE = "chat"
AGENT_DESCRIPTION = "Human-in-the-Loop agent. Pauses on sensitive actions and waits for approval before proceeding."

trace_log: list[dict] = []

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "memory.db")

SENSITIVE_KEYWORDS = ["delete", "remove", "drop", "send", "deploy", "reset", "sterge", "trimite"]

SYSTEM_PROMPT = """
You are HITL Agent — the 9th agent in the LangGraph learning series.
Your purpose: demonstrate Human-in-the-Loop execution using interrupt() and Command(resume=).
Concepts you teach: interrupt(), Command(resume=), approval gate, checkpoint restore, sensitive action detection.
If asked who you are or why you exist — explain exactly this.

When you are asked to confirm or approve an action — it means the system detected a sensitive request.
Ask the user clearly: is this action approved? Wait for 'approve' or 'reject'.
If approved — confirm the action was executed.
If rejected — confirm the action was cancelled.

Only answer questions related to this agent, its concepts, LangGraph, or the AI Playground Framework we are building.
If the user asks about anything else — politely decline and redirect them to the topics above.
"""

llm = ChatOpenAI(
    model=LLM_MODEL,
    base_url=LLM_PROXY,
    api_key=LLM_API_KEY,
    temperature=0.7,
)


def node_detect(state: MessagesState) -> dict:
    last_message = state["messages"][-1].content

    trace_log.append({
        "type": "node_exec",
        "label": "node_detect",
        "from": "graph",
        "to": "classifier",
        "arrow": "->",
        "content": f"checking: {last_message[:100]}",
    })

    if any(kw in last_message.lower() for kw in SENSITIVE_KEYWORDS):
        decision = interrupt({
            "question": "Sensitive action detected. Do you approve? Reply 'approve' or 'reject'.",
            "action": last_message,
        })

        trace_log.append({
            "type": "tool_result",
            "label": "HITL",
            "from": "human",
            "to": "graph",
            "arrow": "->",
            "content": f"human decision: {decision}",
        })

        if str(decision).lower() == "approve":
            return {"messages": state["messages"] + [AIMessage(content=f"Approved. Executing: {last_message}")]}
        else:
            return {"messages": state["messages"] + [AIMessage(content="Action rejected. Nothing was executed.")]}

    return {"messages": state["messages"]}


def node_chat(state: MessagesState) -> dict:
    messages = state["messages"]

    if not any(isinstance(m, SystemMessage) for m in messages):
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages

    trace_log.append({
        "type": "node_exec",
        "label": "node_chat",
        "from": "graph",
        "to": "llm",
        "arrow": "->",
        "content": f"messages in history: {len(messages)}",
    })

    response = llm.invoke(messages, config={"callbacks": [langfuse_handler]})

    trace_log.append({
        "type": "llm_response",
        "label": "LLM",
        "from": "llm",
        "to": "user",
        "arrow": "->",
        "content": str(response.content)[:200],
    })

    return {"messages": state["messages"] + [response]}


def build_graph():
    conn = SqliteSaver(sqlite3.connect(DB_PATH, check_same_thread=False))
    g = StateGraph(MessagesState)
    g.add_node("detect", node_detect)
    g.add_node("chat", node_chat)
    g.add_edge(START, "detect")
    g.add_edge("detect", "chat")
    g.add_edge("chat", END)
    return g.compile(checkpointer=conn)


_graph = build_graph()


def run_agent(payload) -> str:
    trace_log.clear()

    if isinstance(payload, str):
        user_input = payload
        thread_id = "default"
    else:
        user_input = payload.get("message", "")
        thread_id = payload.get("thread_id", "default")

    if not user_input:
        return "No message provided."

    config = {"configurable": {"thread_id": thread_id}}

    # Check if graph is suspended (waiting for human approval)
    state = _graph.get_state(config)
    if state.next:
        decision = user_input.strip().lower()
        result = _graph.invoke(Command(resume=decision), config=config)
    else:
        result = _graph.invoke(
            {"messages": [HumanMessage(content=user_input)]},
            config=config,
        )

    return result["messages"][-1].content or ""
