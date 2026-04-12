"""
Agent 12 — Structured Output Agent
Pattern: Guaranteed JSON extraction using Pydantic + with_structured_output().
Teaches: Pydantic BaseModel, llm.with_structured_output(), typed LLM responses.

Instead of asking the LLM to "please return JSON", we bind a Pydantic schema
directly to the LLM — it cannot return anything else. If the output doesn't
match the schema, LangChain raises an error before it reaches your code.

Flow:
  user text (free form, any language)
    → node_extract: structured LLM extracts fields → PersonProfile (guaranteed JSON)
    → run_agent returns dict — not string
"""

from typing import TypedDict, Optional

from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, START, END

from src.config import LLM_MODEL, LLM_PROXY, LLM_API_KEY, langfuse_handler

AGENT_NAME = "Structured Output Agent"
AGENT_TYPE = "chat"
AGENT_DESCRIPTION = "Extracts structured data from free-form text using Pydantic schema and with_structured_output(). Returns guaranteed JSON — name, age, city, role."

trace_log: list[dict] = []


class PersonProfile(BaseModel):
    name: str = Field(description="Full name of the person")
    age: Optional[int] = Field(description="Age in years as an integer")
    city: Optional[str] = Field(description="City or location mentioned")
    role: Optional[str] = Field(description="Job title, role, or profession")


SYSTEM_PROMPT = """
You are Structured Output Agent — the twelfth agent in the LangGraph learning series.
Your purpose: extract structured person data from free-form text input.
Concepts you teach: Pydantic BaseModel, with_structured_output(), guaranteed JSON extraction.
If asked who you are or why you exist — explain exactly this.

Extract the following fields from the user's text:
- name: full name of the person (required)
- age: age in years as integer (optional — null if not mentioned)
- city: city or location (optional — null if not mentioned)
- role: job title or profession (optional — null if not mentioned)

If a field is not present in the text, return null for that field.
Do not invent information that is not in the text.
Only process requests that contain person data to extract.
Only answer questions related to this agent, its concepts, LangGraph, or the AI Playground Framework we are building.
If the user asks about anything else — politely decline and redirect them to the topics above.
"""

llm = ChatOpenAI(
    model=LLM_MODEL,
    base_url=LLM_PROXY,
    api_key=LLM_API_KEY,
    temperature=0.0,
)

structured_llm = llm.with_structured_output(PersonProfile)


class State(TypedDict):
    input: str
    profile: dict


def node_extract(state: State) -> dict:
    trace_log.append({
        "type": "node_exec",
        "label": "Extract",
        "from": "user",
        "to": "llm",
        "arrow": "->",
        "content": state["input"][:200],
        "fn": "node_extract",
    })

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=state["input"]),
    ]

    result: PersonProfile = structured_llm.invoke(
        messages, config={"callbacks": [langfuse_handler]}
    )

    profile = result.model_dump()

    trace_log.append({
        "type": "llm_response",
        "label": "Profile",
        "from": "llm",
        "to": "user",
        "arrow": "->",
        "content": str(profile)[:200],
        "fn": "node_extract",
    })

    return {"profile": profile}


def build_graph():
    g = StateGraph(State)
    g.add_node("extract", node_extract)
    g.add_edge(START, "extract")
    g.add_edge("extract", END)
    return g.compile()


_graph = build_graph()


def run_agent(payload: str) -> dict:
    trace_log.clear()
    result = _graph.invoke({"input": payload, "profile": {}})
    return result["profile"]
