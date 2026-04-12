"""
Agent 11 — Streaming Agent
Pattern: Token streaming — LLM response delivered chunk by chunk.
Teaches: llm.stream(), Python generator (yield), Gradio incremental output.

Flow:
  user input
    → llm.stream(): yields one token at a time
    → run_agent(): yields each chunk to Studio
    → Studio: updates chatbox incrementally — like ChatGPT
"""

from typing import Generator

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from src.config import LLM_MODEL, LLM_PROXY, LLM_API_KEY, langfuse_handler, get_llm_temperature

AGENT_NAME = "Streaming Agent"
AGENT_TYPE = "streaming"
AGENT_DESCRIPTION = "Demonstrates token streaming — LLM response delivered chunk by chunk using llm.stream() and Python generators."

trace_log: list[dict] = []

SYSTEM_PROMPT = """
You are Streaming Agent — the eleventh agent in the LangGraph learning series.
Your purpose: demonstrate token streaming — delivering LLM responses chunk by chunk.
Concepts you teach: llm.stream(), Python generators, yield, Gradio incremental output.
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


def run_agent(payload: str) -> Generator[str, None, None]:
    trace_log.clear()
    trace_log.append({
        "type": "node_exec",
        "label": "User",
        "from": "user",
        "to": "llm",
        "arrow": "->",
        "content": payload[:200],
        "fn": "run_agent",
    })

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=payload),
    ]

    full_response = ""
    for chunk in llm.stream(messages, config={"callbacks": [langfuse_handler]}):
        token = chunk.content or ""
        full_response += token
        yield token

    trace_log.append({
        "type": "llm_response",
        "label": "LLM",
        "from": "llm",
        "to": "user",
        "arrow": "->",
        "content": full_response[:200],
        "model": llm.model_name,
        "temperature": get_llm_temperature(llm, 0.7),
        "fn": "run_agent",
    })
