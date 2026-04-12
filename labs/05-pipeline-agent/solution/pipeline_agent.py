"""
Agent 5 — Pipeline Agent
Pattern: Nodes in series — each node processes the output of the previous one.
Teaches: deterministic sequential flow, multiple state fields, no branching.

Pipeline: input -> node_extract -> node_transform -> node_respond -> output

Difference from Agent 4 (Router):
- Agent 4: one node runs (branching chooses which one)
- Agent 5: ALL nodes always run, in fixed order

Key strength of the pipeline pattern — per-node model assignment:
- node_extract  → llm_fast (gpt-5.4-nano, temperature=0.0) — ultra cheap, deterministic, ideal for classification
- node_transform → llm_fast (gpt-5.4-nano, temperature=0.0) — ultra cheap, deterministic, ideal for reformulation
- node_respond  → llm_smart (gpt-5.1, temperature=0.7)       — powerful, creative

Each node is independent — you can swap the model at any node without touching the others.
This is impossible with a single LLM call approach.
"""

from langgraph.graph import StateGraph, START, END
from langchain_core.messages import SystemMessage, HumanMessage
from src.config import LLM_MODEL, LLM_PROXY, LLM_API_KEY, langfuse_handler, get_llm_temperature
from langchain_openai import ChatOpenAI
from typing import TypedDict

AGENT_NAME = "Pipeline Agent"
AGENT_TYPE = "pipeline"
AGENT_DESCRIPTION = "Demonstrates deterministic sequential flow: extract → transform → respond. Teaches: multiple nodes in series, multiple state fields, fixed execution order."

trace_log: list[dict] = []

# Fast model — ultra cheap and deterministic, used for mechanical processing steps (extract, classify, reformulate)
llm_fast = ChatOpenAI(
    model="gpt-5.4-nano",
    base_url=LLM_PROXY,
    api_key=LLM_API_KEY,
    temperature=0.0,
)

# Smart model — powerful and creative, used only for the final user-facing response
llm_smart = ChatOpenAI(
    model="gpt-5.1",
    base_url=LLM_PROXY,
    api_key=LLM_API_KEY,
    temperature=0.7,
)

class State(TypedDict):
    raw_input: str
    extracted: str
    transformed: str
    response: str

SYSTEM_PROMPT = """
You are Pipeline Agent — the fifth agent in the LangGraph learning series.
Your purpose: demonstrate deterministic sequential flow — every node always runs in fixed order.
Concepts you teach: multiple nodes in series, multiple state fields, fixed execution order, no branching.
If asked who you are or why you exist — explain exactly this.
Only answer questions related to this agent, its concepts, LangGraph, or the AI Playground Framework we are building.
If the user asks about anything else — politely decline and redirect them to the topics above.
"""

def node_extract(state: State) -> dict:
    trace_log.append({
        "type": "node_exec",
        "label": "Extract",
        "from": "user",
        "to": "extract",
        "arrow": "->",
        "content": state["raw_input"][:200],
        "fn": "node_extract",
    })
    prompt = [
        SystemMessage(content="Extract the key intent and main topic from the user message. Return only a short summary — one sentence maximum."),
        HumanMessage(content=state["raw_input"]),
    ]
    response = llm_fast.invoke(prompt, config={"callbacks": [langfuse_handler]})
    trace_log[-1]["model"] = llm_fast.model_name
    trace_log[-1]["temperature"] = get_llm_temperature(llm_fast, 0.0)
    return {"extracted": response.content}

def node_transform(state: State) -> dict:
    trace_log.append({
        "type": "node_exec",
        "label": "Transform",
        "from": "extract",
        "to": "transform",
        "arrow": "->",
        "content": state["extracted"][:200],
        "fn": "node_transform",
    })
    prompt = [
        SystemMessage(content="Take the extracted intent and reformulate it into a clear, well-structured question or actionable statement. Return only one sentence."),
        HumanMessage(content=state["extracted"]),
    ]
    response = llm_fast.invoke(prompt, config={"callbacks": [langfuse_handler]})
    trace_log[-1]["model"] = llm_fast.model_name
    trace_log[-1]["temperature"] = get_llm_temperature(llm_fast, 0.0)
    trace_log[-1]["node"] = "node_transform"
    return {"transformed": response.content}

def node_respond(state: State) -> dict:
    prompt = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=state["transformed"]),
    ]
    response = llm_smart.invoke(prompt, config={"callbacks": [langfuse_handler]})
    trace_log.append({
        "type": "llm_response",
        "label": "Respond",
        "from": "respond",
        "to": "user",
        "arrow": "->",
        "content": response.content[:200],
        "model": llm_smart.model_name,
        "temperature": get_llm_temperature(llm_smart, 0.7),
        "fn": "node_respond",
    })
    return {"response": response.content}

def build_graph():
    g = StateGraph(State)
    g.add_node("extract", node_extract)
    g.add_node("transform", node_transform)
    g.add_node("respond", node_respond)
    g.add_edge(START, "extract")
    g.add_edge("extract", "transform")
    g.add_edge("transform", "respond")
    g.add_edge("respond", END)
    return g.compile()

_graph = build_graph()

def run_agent(payload: str) -> str:
    trace_log.clear()
    result = _graph.invoke({
        "raw_input": payload,
        "extracted": "",
        "transformed": "",
        "response": "",
    })
    return result["response"] or ""
