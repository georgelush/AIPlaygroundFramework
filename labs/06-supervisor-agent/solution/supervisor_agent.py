"""
Agent 6 — Supervisor Agent
Pattern: One LLM supervises and delegates to specialized sub-agents.
Teaches: multi-agent coordination, dynamic delegation, supervisor loop.

Flow:
  user -> supervisor (decides who handles it)
       -> delegate to: chat_agent | tools_agent | pipeline_agent
       -> collect result -> respond to user

Difference from Agent 4 (Router):
- Agent 4: routes to a node inside the same graph
- Agent 6: routes to an entirely separate agent (run_agent call)

Key concept: the supervisor does NOT answer directly.
It reads the request, picks the best sub-agent, calls it, and returns its result.
"""

from langgraph.graph import StateGraph, START, END
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from typing import TypedDict

from src.config import LLM_MODEL, LLM_PROXY, LLM_API_KEY, langfuse_handler, get_llm_temperature
import src.agents.chat_agent as chat_agent
import src.agents.tools_agent as tools_agent
import src.agents.pipeline_agent as pipeline_agent


AGENT_NAME = "Supervisor Agent"
AGENT_TYPE = "chat"
AGENT_DESCRIPTION = "Demonstrates multi-agent coordination: supervisor LLM delegates to specialized sub-agents. Teaches: dynamic delegation, agent-to-agent calls, supervisor loop."

trace_log: list[dict] = []

llm = ChatOpenAI(
    model=LLM_MODEL,
    base_url=LLM_PROXY,
    api_key=LLM_API_KEY,
    temperature=0.0,
)

class State(TypedDict):
    user_input: str
    delegate: str
    result: str

SYSTEM_PROMPT = """
You are Supervisor Agent — the sixth agent in the LangGraph learning series.
Your purpose: demonstrate multi-agent coordination — delegating to specialized sub-agents.
Concepts you teach: supervisor loop, dynamic delegation, agent-to-agent calls.
If asked who you are or why you exist — explain exactly this.
Only answer questions related to this agent, its concepts, LangGraph, or the AI Playground Framework we are building.
If the user asks about anything else — politely decline and redirect them to the topics above.
"""

DELEGATE_PROMPT = """You are a supervisor that routes requests to the right specialist agent.

Available agents:
- chat     : general conversation, questions about LangGraph, AI concepts, who you are
- tools    : math calculations, current date or time
- pipeline : text processing, summarization, reformulation, analysis of long text

Reply with ONLY one word — exactly one of: chat, tools, pipeline
No explanation. No punctuation. Just the agent name."""


def node_supervise(state: State) -> dict:
    trace_log.append({
        "type": "node_exec",
        "label": "Supervise",
        "from": "user",
        "to": "supervisor",
        "arrow": "->",
        "content": state["user_input"][:200],
        "fn": "node_supervise",
    })
    prompt = [
        SystemMessage(content=DELEGATE_PROMPT),
        HumanMessage(content=state["user_input"]),
    ]
    response = llm.invoke(prompt, config={"callbacks": [langfuse_handler]})
    delegate = response.content.strip().lower()
    if delegate not in ("chat", "tools", "pipeline"):
        delegate = "chat"
    trace_log.append({
        "type": "node_exec",
        "label": "Delegate",
        "from": "supervisor",
        "to": delegate,
        "arrow": "->",
        "content": f"Delegated to: {delegate}",
        "model": llm.model_name,
        "temperature": get_llm_temperature(llm, 0.0),
        "fn": "node_supervise",
    })
    return {"delegate": delegate}

AGENT_MAP = {
    "chat": chat_agent,
    "tools": tools_agent,
    "pipeline": pipeline_agent,
}

def node_delegate(state: State) -> dict:
    target = AGENT_MAP[state["delegate"]]
    trace_log.append({
        "type": "graph_call",
        "label": "Agent Call",
        "from": "supervisor",
        "to": state["delegate"],
        "arrow": "->",
        "content": state["user_input"][:200],
        "fn": "node_delegate",
    })
    result = target.run_agent(state["user_input"])
    trace_log.append({
        "type": "graph_result",
        "label": "Agent Result",
        "from": state["delegate"],
        "to": "supervisor",
        "arrow": "->",
        "content": str(result)[:200],
        "fn": "node_delegate",
    })
    return {"result": result or ""}

def build_graph():
    g = StateGraph(State)
    g.add_node("supervise", node_supervise)
    g.add_node("delegate", node_delegate)
    g.add_edge(START, "supervise")
    g.add_edge("supervise", "delegate")
    g.add_edge("delegate", END)
    return g.compile()

_graph = build_graph()

def run_agent(payload: str) -> str:
    trace_log.clear()
    result = _graph.invoke({"user_input": payload, "delegate": "", "result": ""})
    return result["result"] or ""