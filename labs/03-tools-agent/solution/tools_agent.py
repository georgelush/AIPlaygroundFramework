"""
Agent 3 — Tools Agent
Pattern: ReAct loop — LLM + ToolNode + tools_condition.
Teaches: @tool, ToolNode, tools_condition, tool calling cycle.
"""

from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.tools import tool
from src.config import LLM_MODEL, LLM_PROXY, LLM_API_KEY, langfuse_handler, get_llm_temperature
from langchain_openai import ChatOpenAI

AGENT_NAME = "Tools Agent"
AGENT_TYPE = "chat"
AGENT_DESCRIPTION = "Demonstrates ReAct loop: LLM decides when to call tools. Teaches: @tool, ToolNode, tools_condition."

trace_log: list[dict] = []

SYSTEM_PROMPT = """
You are Tools Agent — the third agent in the LangGraph learning series.
Your purpose: demonstrate the ReAct loop — LLM deciding when to call tools.
Concepts you teach: @tool decorator, ToolNode, tools_condition, tool calling cycle.
You have access to two tools: get_current_time and calculate. Always use a tool when the question requires it.
If asked who you are or why you exist — explain exactly this.
Only answer questions related to this agent, its concepts, LangGraph, or the AI Playground Framework we are building.
If the user asks about anything else — politely decline and redirect them to the topics above.
"""


@tool
def get_current_time() -> str:
    """Returns the current date and time.
    Use this when the user asks what time or date it is."""
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

@tool
def calculate(expression: str) -> str:
    """Evaluates a mathematical expression and returns the result.
    Use this when the user asks to calculate or compute something.
    Example expressions: '2 + 2', '10 * 5', '100 / 4'."""
    try:
        result = eval(expression, {"__builtins__": {}}, {})
        return str(result)
    except Exception as e:
        return f"Error: {e}"


TOOLS = [get_current_time, calculate]

llm = ChatOpenAI(
    model=LLM_MODEL,
    base_url=LLM_PROXY,
    api_key=LLM_API_KEY,
    temperature=0.7,
)

llm_with_tools = llm.bind_tools(TOOLS)

def node_llm(state: MessagesState) -> dict:
    last = state["messages"][-1]
    if isinstance(last, HumanMessage):
        trace_log.append({
            "type": "node_exec",
            "label": "User",
            "from": "user",
            "to": "llm",
            "arrow": "->",
            "content": str(last.content)[:200],
            "fn": "node_llm",
        })
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    response = llm_with_tools.invoke(messages, config={"callbacks": [langfuse_handler]})
    if response.tool_calls:
        trace_log.append({
            "type": "tool_call",
            "label": "Tool Call",
            "from": "llm",
            "to": "tools",
            "arrow": "->",
            "content": str(response.tool_calls[0]["name"]),
            "model": llm.model_name,
            "temperature": get_llm_temperature(llm, 0.7),
            "fn": response.tool_calls[0]["name"],
        })
    else:
        trace_log.append({
            "type": "llm_response",
            "label": "LLM",
            "from": "llm",
            "to": "user",
            "arrow": "->",
            "content": str(response.content)[:200],
            "model": llm.model_name,
            "temperature": get_llm_temperature(llm, 0.7),
            "fn": "node_llm",
        })
    return {"messages": state["messages"] + [response]}

def node_tools(state: MessagesState) -> dict:
    last = state["messages"][-1]
    trace_log.append({
        "type": "tool_result",
        "label": "Tool Result",
        "from": "tools",
        "to": "llm",
        "arrow": "->",
        "content": str(last.content)[:200],
        "fn": getattr(last, "name", "tool"),
    })
    return {}

def build_graph():
    tool_node = ToolNode(TOOLS)
    g = StateGraph(MessagesState)
    g.add_node("llm", node_llm)
    g.add_node("tools", tool_node)
    g.add_node("tool_log", node_tools)
    g.add_edge(START, "llm")
    g.add_conditional_edges("llm", tools_condition)
    g.add_edge("tools", "tool_log")
    g.add_edge("tool_log", "llm")
    return g.compile()

_graph = build_graph()

def run_agent(payload: str) -> str:
    trace_log.clear()
    result = _graph.invoke(
        {"messages": [HumanMessage(content=payload)]},
    )
    return result["messages"][-1].content or ""