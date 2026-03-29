# GitHub Copilot Instructions

## Project Overview
This is a custom LangGraph agent framework. Agents are auto-discovered from `src/agents/`
and exposed via a Gradio debug UI (`studio.py`) and a FastAPI REST server (`server.py`).

---

## Tech Stack
- **LangGraph** 1.1.3 — agent graphs, StateGraph, ToolNode
- **LangChain** — ChatOpenAI, bind_tools, tool decorator
- **FastAPI** + **uvicorn** — REST API server
- **Gradio** 6.x — local debug UI
- **Langfuse** — LLM observability/tracing
- **LiteLLM proxy** — LLM gateway (model: gpt-5.1)

---

## Project Structure
```
src/
├── agents/      # Orchestrators — LLM + tools + graph + trace_log
├── graphs/      # StateGraph definitions — nodes + edges + flow
├── nodes/       # Atomic node functions — receive state, return partial state
├── tools/       # @tool functions — called by LLM dynamically
├── registry.py  # Auto-discovery — shared by studio.py and server.py
└── config.py    # Shared config (env vars, LLM client, Langfuse handler)

studio.py        # Gradio debug UI — local development only (port 8000)
server.py        # FastAPI REST server — production / n8n (port 8080)
```

---

## Agent Contract
Every file in `src/agents/` **must** follow this contract to be auto-registered:

```python
AGENT_NAME = "My Agent"              # display name in UI and API
AGENT_TYPE = "chat"                  # "chat" | "processor" | "pipeline"
AGENT_DESCRIPTION = "Does X and Y"  # shown in GET /agents

trace_log: list[dict] = []          # never reassign — always use .clear()

def run_agent(payload) -> str | dict:
    trace_log.clear()
    # ... logic
    return result
```

---

## State Rules (LangGraph)
- Always define State as `TypedDict`
- Node functions return **only the fields they modified** (partial state update)
- Never mutate state in-place — always return a new partial dict

```python
from typing import TypedDict

class State(TypedDict):
    messages: list
    user_input: str

# CORRECT — partial update
def my_node(state: State) -> dict:
    return {"messages": state["messages"] + [new_message]}

# WRONG — never mutate or return full copy unless all fields change
def my_node(state: State) -> State:
    state["messages"].append(new_message)
    return state
```

---

## Trace Log Structure
Every significant execution step must be appended to `trace_log`:

```python
trace_log.append({
    "type": "llm_response",   # see types below
    "label": "LLM",           # short badge text shown in Studio UI
    "from": "user",           # source of the action
    "to": "llm",              # destination of the action
    "arrow": "->",
    "content": str(output)[:200],
})
```

**Trace types:**
| type | color in UI | when to use |
|---|---|---|
| `node_exec` | cyan | a LangGraph node was entered |
| `tool_call` | blue | LLM decided to call a tool |
| `tool_result` | purple | tool returned a result |
| `llm_response` | light purple | LLM produced a final text response |
| `graph_call` | orange | agent invoked a sub-graph |
| `graph_result` | yellow | sub-graph returned a result |

---

## LLM Setup
Always import from `src.config` — never instantiate ChatOpenAI directly in agents:

```python
from src.config import LLM_MODEL, LLM_PROXY, LLM_API_KEY, langfuse_handler
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model=LLM_MODEL,
    base_url=LLM_PROXY,
    api_key=LLM_API_KEY,
    temperature=0.7,
)

# Always pass langfuse_handler as a callback so calls are tracked
response = llm.invoke(messages, config={"callbacks": [langfuse_handler]})

# Add tools with bind_tools when the agent needs tool calling
llm_with_tools = llm.bind_tools(TOOLS)
```

---

## Message Types (LangChain)
```python
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

SystemMessage(content="You are a helpful assistant.")  # instructions, invisible to user
HumanMessage(content="What is on the menu?")           # user input
AIMessage(content="We have pizza and pasta.")          # LLM reply
```

---

## Tools Rules
```python
from langchain_core.tools import tool

@tool
def get_menu() -> str:
    """Returns the full restaurant menu with prices.
    Use this when the customer asks about available dishes or prices."""
    return "Margherita 25 lei, Pepperoni 28 lei..."
```
- Docstring is **mandatory** — the LLM reads it to decide when to call the tool
- Return plain strings or JSON-serializable dicts only
- Always handle exceptions inside the tool — never let errors reach the LLM

---

## Graph Rules
```python
from langgraph.graph import StateGraph, START, END

def build_graph():
    g = StateGraph(State)
    g.add_node("node_name", node_function)
    g.add_edge(START, "node_name")
    g.add_edge("node_name", END)
    return g.compile()

graph = build_graph()  # compile once at module level
```
- Always use a `build_graph()` factory function — never build inline
- Use `add_conditional_edges` for branching based on state values
- Node names: `lowercase_with_underscores`
- Call `g.compile()` once and store the result — reuse it on every invocation

---

## Error Handling
- Validate inputs only at system boundaries (API endpoints, `run_agent` entry point)
- Do not wrap individual nodes in try/except unless they call external services
- FastAPI endpoints use `HTTPException` with proper status codes (404, 500)
- Always guard against `None` returns from LLM calls: `return response.content or ""`
- Always guard against `None` in UI layer: `reply = run_fn(payload) or ""`

## Bug Fix Workflow — Always Follow
When investigating a bug or error:
1. **Investigate** — read the error, identify root cause and all affected layers
2. **Present the fix** — explain what you will change and why this approach over alternatives
3. **Ask for confirmation** — never implement without explicit user approval
4. Only after confirmation → implement the fix

---

## Language Rules — Always Enforce
- **All code comments must be in English** — never Romanian, French, or any other language
- **All agent names (`AGENT_NAME`) must be in English** — Title Case, no diacritics
- **All variable names, function names, node names** — English only
- **Docstrings on tools** — English only (the LLM reads them)
- These rules apply to every file in the project without exception

---

## Naming Conventions
| Thing | Convention | Example |
|---|---|---|
| Agent file | `snake_case.py` | `pitterie_agent.py` |
| Node function | `node_` prefix | `node_respond()`, `node_classify()` |
| Graph builder | `build_graph()` | always this name |
| Tool function | verb + noun | `get_menu()`, `calculate_total()` |
| State class | always `State` | `class State(TypedDict)` |
| `AGENT_NAME` | Title Case English string | `"Pizza Chatbot"`, `"Research Agent"` |

---

## LangGraph Standard — Always Follow

These are non-negotiable rules for every graph, node, and agent in this project:

### Imports
```python
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
```
- Always import `START` and `END` — never use string `"__start__"` or `"__end__"`
- Use `ToolNode` and `tools_condition` from `langgraph.prebuilt` — never implement tool dispatch manually

### Messages State (standard pattern)
When the agent needs conversation memory, always use the built-in `MessagesState`:
```python
from langgraph.graph import MessagesState  # preferred for chat agents

# Or define manually only when extra fields are needed:
from typing import TypedDict
from langchain_core.messages import BaseMessage

class State(TypedDict):
    messages: list[BaseMessage]
```

### Tool Calling Pattern (ReAct loop)
```python
from langgraph.prebuilt import ToolNode, tools_condition

tool_node = ToolNode(TOOLS)

def node_llm(state: State) -> dict:
    response = llm_with_tools.invoke(state["messages"], config={"callbacks": [langfuse_handler]})
    return {"messages": state["messages"] + [response]}

def build_graph():
    g = StateGraph(State)
    g.add_node("llm", node_llm)
    g.add_node("tools", tool_node)
    g.add_edge(START, "llm")
    g.add_conditional_edges("llm", tools_condition)  # routes to "tools" or END
    g.add_edge("tools", "llm")                       # loop back after tool execution
    return g.compile()
```
- Always use `tools_condition` for routing — never write custom routing logic for tool calls
- The tool loop edge always goes `"tools"` → `"llm"` (back to LLM after tool result)

### Graph Invocation
```python
# Always pass a dict matching State shape
result = graph.invoke({"messages": [HumanMessage(content=user_input)]})

# Extract last message from result
final_message = result["messages"][-1].content
```
- Never call `graph.invoke(user_input)` directly — always wrap in `{"messages": [...]}`
- Extract `.content` from the last message — never return raw `BaseMessage` objects

### Conditional Edges
```python
def route(state: State) -> str:
    # must return a node name or END
    last = state["messages"][-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "tools"
    return END

g.add_conditional_edges("llm", route)
```
- Routing functions must return a string matching a registered node name, or `END`
- Never return `None` or raise from a routing function
