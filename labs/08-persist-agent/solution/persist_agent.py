"""
Agent 8 — Persist Agent
Pattern: SqliteSaver — persistent conversation memory across server restarts.
Purpose: Replace in-memory MemorySaver (Lab 02) with a SQLite-backed checkpointer.
Concepts: SqliteSaver, thread_id, checkpoint restore, langgraph.checkpoint.sqlite.
Send any message — the conversation is saved to disk and restored on the next call.
"""

import os
import sqlite3
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.checkpoint.sqlite import SqliteSaver
from src.config import LLM_MODEL, LLM_PROXY, LLM_API_KEY, langfuse_handler

AGENT_NAME = "Persist Agent"
AGENT_TYPE = "chat"
AGENT_DESCRIPTION = "Persistent conversation memory using SqliteSaver. History survives server restarts."

trace_log: list[dict] = []

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "memory.db")

SYSTEM_PROMPT = """
You are Persist Agent — the 8th agent in the LangGraph learning series.
Your purpose: demonstrate persistent conversation memory using SqliteSaver.
Concepts you teach: SqliteSaver, thread_id, checkpoint restore, memory that survives server restarts.
If asked who you are or why you exist — explain exactly this.
Only answer questions related to this agent, its concepts, LangGraph, or the AI Playground Framework we are building.
If the user asks about anything else — politely decline and redirect them to the topics above.
"""

llm = ChatOpenAI(
    model=LLM_MODEL,
    base_url=LLM_PROXY,
    api_key=LLM_API_KEY,
    temperature=0.7,
)


def node_chat(state: MessagesState) -> dict:
    messages = state["messages"]

    # Inject system prompt only on the first message
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
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    checkpointer = SqliteSaver(conn)
    g = StateGraph(MessagesState)
    g.add_node("chat", node_chat)
    g.add_edge(START, "chat")
    g.add_edge("chat", END)
    return g.compile(checkpointer=checkpointer)


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

    result = _graph.invoke(
        {"messages": [HumanMessage(content=user_input)]},
        config=config,
    )

    return result["messages"][-1].content or ""
