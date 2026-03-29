"""
Agent 1 — Hello Agent
Pattern: Simple LLM call, no graph.
Teaches: agent contract, AGENT_NAME, AGENT_TYPE, trace_log, run_agent.
"""


from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from src.config import LLM_MODEL, LLM_PROXY, LLM_API_KEY, langfuse_handler


AGENT_NAME = "Hello Agent"
AGENT_TYPE = "chat"
AGENT_DESCRIPTION = "Simplest possible agent — direct LLM call, no graph. Teaches the agent contract."

trace_log: list[dict] = []

SYSTEM_PROMPT = """
You are Hello Agent — the first agent in the LangGraph learning series.
Your purpose: demonstrate the basic agent contract with no graph.
Concepts you teach: AGENT_NAME, AGENT_TYPE, AGENT_DESCRIPTION, trace_log, run_agent.
If asked who you are or why you exist — explain exactly this.
Only answer questions related to these concepts or to LangGraph learning in general.
If the user asks about anything else — politely decline and redirect them to the topics above.
"""


llm = ChatOpenAI(
    model=LLM_MODEL,
    base_url=LLM_PROXY,
    api_key=LLM_API_KEY,
    temperature=0.7,
)


def run_agent(payload: str) -> str:
    trace_log.clear()
    trace_log.append({
        "type": "llm_response",
        "label": "LLM",
        "from": "user",
        "to": "llm",
        "arrow": "->",
        "content": payload[:200],
    })
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=payload),
    ]
    response = llm.invoke(messages, config={"callbacks": [langfuse_handler]})
    trace_log.append({
        "type": "llm_response",
        "label": "LLM",
        "from": "llm",
        "to": "user",
        "arrow": "->",
        "content": response.content[:200],
    })
    return response.content or ""