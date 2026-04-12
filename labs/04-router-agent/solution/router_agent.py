"""
Agent 4 — Router Agent
Pattern: Conditional branching — classify input, route to different nodes.
Teaches: routing functions, add_conditional_edges, multiple node paths.
"""


from langgraph.graph import StateGraph, START, END
from langchain_core.messages import SystemMessage, HumanMessage
from src.config import LLM_MODEL, LLM_PROXY, LLM_API_KEY, langfuse_handler, get_llm_temperature
from langchain_openai import ChatOpenAI
from typing import TypedDict

AGENT_NAME = "Router Agent"
AGENT_TYPE = "chat"
AGENT_DESCRIPTION = "Demonstrates conditional branching: classifies input and routes to different nodes. Teaches: routing functions, add_conditional_edges."

trace_log: list[dict] = []

llm = ChatOpenAI(
    model=LLM_MODEL,
    base_url=LLM_PROXY,
    api_key=LLM_API_KEY,
    temperature=0.3,
)

class State(TypedDict):
    user_input: str
    route: str
    response: str

SYSTEM_PROMPT = """
You are Router Agent — the fourth agent in the LangGraph learning series.
Your purpose: demonstrate conditional branching — classify input and route to different nodes.
Concepts you teach: routing functions, add_conditional_edges, multiple node paths, TypedDict State.
If asked who you are or why you exist — explain exactly this.
Only answer questions related to this agent, its concepts, LangGraph, or the AI Playground Framework we are building.
If the user asks about anything else — politely decline and redirect them to the topics above.
"""

def node_classify(state: State) -> dict:
    trace_log.append({
        "type": "node_exec",
        "label": "Classify",
        "from": "user",
        "to": "classify",
        "arrow": "->",
        "content": state["user_input"][:200],
        "model": llm.model_name,
        "temperature": get_llm_temperature(llm, 0.3),
        "fn": "node_classify",
    })
    prompt = [
        SystemMessage(content=(
            "Classify the user message into exactly one of these categories: "
            "'question', 'greeting', 'other'. "
            "Reply with only the category word — nothing else."
        )),
        HumanMessage(content=state["user_input"]),
    ]
    response = llm.invoke(prompt, config={"callbacks": [langfuse_handler]})
    route = response.content.strip().lower()
    if route not in ("question", "greeting", "other"):
        route = "other"
    trace_log.append({
        "type": "node_exec",
        "label": "Route",
        "from": "classify",
        "to": route,
        "arrow": "->",
        "content": f"Routed to: {route}",
        "fn": "node_classify",
    })
    return {"route": route}

def node_answer_question(state: State) -> dict:
    prompt = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=state["user_input"]),
    ]
    response = llm.invoke(prompt, config={"callbacks": [langfuse_handler]})
    trace_log.append({
        "type": "llm_response",
        "label": "Answer",
        "from": "answer_question",
        "to": "user",
        "arrow": "->",
        "content": response.content[:200],
        "model": llm.model_name,
        "temperature": get_llm_temperature(llm, 0.3),
        "fn": "node_answer_question",
    })
    return {"response": response.content}

def node_greet(state: State) -> dict:
    prompt = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=state["user_input"]),
    ]
    response = llm.invoke(prompt, config={"callbacks": [langfuse_handler]})
    trace_log.append({
        "type": "llm_response",
        "label": "Greet",
        "from": "greet",
        "to": "user",
        "arrow": "->",
        "content": response.content[:200],
        "model": llm.model_name,
        "temperature": get_llm_temperature(llm, 0.3),
        "fn": "node_greet",
    })
    return {"response": response.content}


def node_fallback(state: State) -> dict:
    prompt = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=state["user_input"]),
    ]
    response = llm.invoke(prompt, config={"callbacks": [langfuse_handler]})
    trace_log.append({
        "type": "llm_response",
        "label": "Fallback",
        "from": "fallback",
        "to": "user",
        "arrow": "->",
        "content": response.content[:200],
        "model": llm.model_name,
        "temperature": get_llm_temperature(llm, 0.3),
        "fn": "node_fallback",
    })
    return {"response": response.content}

def route_by_type(state: State) -> str:
    if state["route"] == "question":
        return "answer_question"
    elif state["route"] == "greeting":
        return "greet"
    return "fallback"


def build_graph():
    g = StateGraph(State)
    g.add_node("classify", node_classify)
    g.add_node("answer_question", node_answer_question)
    g.add_node("greet", node_greet)
    g.add_node("fallback", node_fallback)
    g.add_edge(START, "classify")
    g.add_conditional_edges("classify", route_by_type)
    g.add_edge("answer_question", END)
    g.add_edge("greet", END)
    g.add_edge("fallback", END)
    return g.compile()

_graph = build_graph()

def run_agent(payload: str) -> str:
    trace_log.clear()
    result = _graph.invoke({"user_input": payload, "route": "", "response": ""})
    return result["response"] or ""