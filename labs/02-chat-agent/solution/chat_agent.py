"""
Agent 2 — Chat Agent
Pattern: Single-node StateGraph with in-session memory.
Teaches: StateGraph, START, END, MessagesState, MemorySaver, thread_id.
"""

from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import SystemMessage, HumanMessage
from src.config import LLM_MODEL, LLM_PROXY, LLM_API_KEY, langfuse_handler, get_llm_temperature
from langchain_openai import ChatOpenAI

AGENT_NAME = "Chat Agent"
AGENT_TYPE = "chat"
AGENT_DESCRIPTION = "Demonstrates single-node StateGraph with in-session memory. Teaches: StateGraph, START, END, MessagesState, MemorySaver, thread_id."

trace_log: list[dict] = []

SYSTEM_PROMPT = """
You are Chat Agent — the second agent in the LangGraph learning series.
Your purpose: demonstrate a single-node StateGraph with in-session memory using MemorySaver.
Concepts you teach: StateGraph, START, END, MessagesState, MemorySaver, thread_id.
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
    user_input = state["messages"][-1].content
    trace_log.append({
        "type": "node_exec",
        "label": "User",
        "from": "user",
        "to": "llm",
        "arrow": "->",
        "content": str(user_input)[:200],
        "fn": "node_chat",
    })
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    response = llm.invoke(messages, config={"callbacks": [langfuse_handler]})
    trace_log.append({
        "type": "llm_response",
        "label": "LLM",
        "from": "llm",
        "to": "user",
        "arrow": "->",
        "content": str(response.content)[:200],
        "model": llm.model_name,
        "temperature": get_llm_temperature(llm, 0.7),
        "fn": "node_chat",
    })
    return {"messages": state["messages"] + [response]}

def build_graph():
    memory = MemorySaver()
    g = StateGraph(MessagesState)
    g.add_node("chat", node_chat)
    g.add_edge(START, "chat")
    g.add_edge("chat", END)
    return g.compile(checkpointer=memory)

_graph = build_graph()

def run_agent(payload: str) -> str:
    trace_log.clear()
    config = {"configurable": {"thread_id": "default"}}
    result = _graph.invoke(
        {"messages": [HumanMessage(content=payload)]},
        config=config,
    )
    return result["messages"][-1].content or ""
