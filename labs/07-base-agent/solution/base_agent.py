"""
Agent 7 — Base Agent
Pattern: BaseAgent class with Mixins — CostTrackingMixin, LoggingMixin, AuthMixin.
Purpose: Demonstrate how to structure a production agent using reusable mixins.
Concepts: Mixin classes, multiple inheritance, cost tracking, logging, auth context.
Send any message — replies using gpt-5.1 via LiteLLM proxy with full observability.
"""

from typing import TypedDict
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage
from langgraph.graph import StateGraph, START, END
from src.config import LLM_MODEL, LLM_PROXY, LLM_API_KEY, langfuse_handler
from src.mixins.cost_tracking import CostTrackingMixin
from src.mixins.logging_mixin import LoggingMixin
from src.mixins.auth_mixin import AuthMixin

AGENT_NAME = "Base Agent"
AGENT_TYPE = "chat"
AGENT_DESCRIPTION = "Agent 7 — Production-ready chat agent with CostTrackingMixin, LoggingMixin, and AuthMixin. Demonstrates how to structure reusable, observable agents using multiple inheritance."

trace_log: list[dict] = []

SYSTEM_PROMPT = """
You are Base Agent — the 7th agent in the LangGraph learning series.
Your purpose: demonstrate how to structure a production agent using reusable mixin classes.
Concepts you teach: CostTrackingMixin, LoggingMixin, AuthMixin, multiple inheritance, BaseAgent pattern.
If asked who you are or why you exist — explain exactly this.
Only answer questions related to this agent, its concepts, LangGraph, or the AI Playground Framework we are building.
If the user asks about anything else — politely decline and redirect them to the topics above.
"""

class State(TypedDict):
    messages: list[BaseMessage]
    user_id: str
    role: str


class BaseAgent(CostTrackingMixin, LoggingMixin, AuthMixin):

    def __init__(self):
        CostTrackingMixin.__init__(self)
        AuthMixin.__init__(self)
        self.llm = ChatOpenAI(
            model=LLM_MODEL,
            base_url=LLM_PROXY,
            api_key=LLM_API_KEY,
            temperature=0.7,
        )

    def node_llm(self, state: State) -> dict:
        self.log_step("node_llm", f"user={self.get_user_id()}")
        trace_log.append({
            "type": "node_exec",
            "label": "node_llm",
            "from": "graph",
            "to": "llm",
            "arrow": "->",
            "content": f"user={self.get_user_id()} | role={self._user_role}",
        })

        messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
        response = self.llm.invoke(messages, config={"callbacks": [langfuse_handler]})

        usage = self.track_usage(response, model=LLM_MODEL)
        self.log_info(f"tokens={usage['input_tokens']}+{usage['output_tokens']} cost=${usage['cost_usd']}")

        trace_log.append({
            "type": "llm_response",
            "label": "LLM",
            "from": "llm",
            "to": "user",
            "arrow": "->",
            "content": (response.content or "")[:200],
            "cost": f"Tokens - in={usage['input_tokens']} / out={usage['output_tokens']} || ${usage['cost_usd']:.6f}",
        })

        return {"messages": state["messages"] + [response]}


def build_graph(agent: BaseAgent):
    g = StateGraph(State)
    g.add_node("llm", agent.node_llm)
    g.add_edge(START, "llm")
    g.add_edge("llm", END)
    return g.compile()

def run_agent(payload) -> str:
    trace_log.clear()

    if isinstance(payload, str):
        import json
        try:
            payload = json.loads(payload)
        except (json.JSONDecodeError, ValueError):
            pass

    user_input = payload.get("message", "") if isinstance(payload, dict) else str(payload)
    user_id = payload.get("user_id", "anonymous") if isinstance(payload, dict) else "anonymous"
    role = payload.get("role", "user") if isinstance(payload, dict) else "user"

    agent = BaseAgent()
    agent.set_auth_context(user_id=user_id, role=role)

    trace_log.append({
        "type": "node_exec",
        "label": "INPUT",
        "from": "user",
        "to": "graph",
        "arrow": "->",
        "content": user_input[:200],
    })

    graph = build_graph(agent)

    result = graph.invoke({
        "messages": [HumanMessage(content=user_input)],
        "user_id": user_id,
        "role": role,
    })

    return result["messages"][-1].content or ""
