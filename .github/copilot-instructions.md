# GitHub Copilot Instructions

## Architecture Philosophy — Always Follow

This project targets **production, large-scale systems**. Every decision must reflect this:

- Always choose the architecturally correct solution — never the shortcut
- Separate concerns: mixins in `src/mixins/`, nodes in `src/nodes/`, tools in `src/tools/`
- Make code reusable across agents — no copy-paste logic between files
- Async where it makes sense — never block on I/O in a production path
- Langfuse callback on every single LLM call — no exceptions
- Validate inputs at system boundaries only (`run_agent` entry point, FastAPI endpoints)
- No try/except inside nodes unless calling external services

---

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
Agentic-AI-Playground/
├── src/
│   ├── agents/          # Active agents — auto-loaded by registry
│   │   └── ping_agent.py
│   ├── graphs/          # StateGraph definitions (shared graphs)
│   ├── nodes/           # Reusable node functions
│   ├── tools/           # Reusable @tool functions
│   ├── mixins/          # Reusable mixins (CostTrackingMixin, LoggingMixin, AuthMixin)
│   ├── config.py        # LLM client, Langfuse handler, env vars
│   └── registry.py      # Agent auto-discovery
├── labs/                # 20-lab curriculum (01–13 ✅  |  14–16 ✅  |  17–20 🔜)
│   ├── README.md        # Curriculum overview + standards
│   ├── GETTING_STARTED.md  # Full setup + framework walkthrough
│   └── 01–20/           # each lab: INSTRUCTIONS.md + solution/xx_agent.py
├── tests/
├── studio.py            # Gradio debug UI (port 8000)
├── server.py            # FastAPI REST server (port 8080)
├── compose.yml          # Docker services (Redis, PostgreSQL)
├── .env.example
└── requirements.txt
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

## Learn Mode — Always Follow When Activated

When the user types **"Learn Mode — I want to build 01 Hello Agent"** (using the lab number and name), switch to block-by-block teaching mode:

- **CRITICAL — Use the existing solution as the only reference:** Before starting, always read the corresponding solution file from `labs/XX-agent-name/solution/xx_agent.py`. Teach EXACTLY what is in that file — block by block. Never invent a different implementation, never add extra tools or nodes that don't exist in the solution. The solution file is the source of truth.
- **ALSO READ INSTRUCTIONS.md:** Before starting, always read `labs/XX-agent-name/INSTRUCTIONS.md`. Use the Test Checklist from that file verbatim — never invent tests. Use the concept list from that file — never add concepts that are not in it. INSTRUCTIONS.md + solution file together are the only source of truth.
- **FIRST ACTION — Create the file:** Before giving Block 1, always tell the user to create the target file. Use this exact format:
  > "Before we start, create this file:
  > **Path:** `src/agents/hello_agent.py`
  > Leave it completely empty — we will fill it block by block."
  > (Use the correct `xx_agent.py` name matching the lab — e.g. `chat_agent.py`, `hitl_agent.py`, `async_agent.py`)
- **Same rule for any new file in the project** (tools, nodes, graphs): whenever a new file is needed in a different folder, stop and tell the user the exact path before continuing.
- **Assume zero knowledge:** explain every concept as if the user has never seen Python, LangGraph, or LLMs before. Use simple analogies. Never assume the user has any idea how to build an agent.
- Give one logical block at a time: docstring → imports → contract vars → SYSTEM_PROMPT → one tool → one node → graph → entry point
- After each block, explain: what it does, why it's written this way, what changes if written differently
- Wait for the user to say **"next"** (or "done") before giving the next block
- Never skip ahead — never give two blocks at once
- At the end, run the agent together in Studio to verify it works
- After giving the `run_agent()` block, always provide the **Test Checklist taken verbatim from `labs/XX-agent-name/INSTRUCTIONS.md`** — never generate your own tests. If the INSTRUCTIONS.md has no test checklist, use the trace log section from that file to construct the tests. Never invent inputs or expected outputs that are not in the INSTRUCTIONS.md.

**Block order for a standard agent:**
1. Docstring
2. Imports
3. Contract vars (`AGENT_NAME`, `AGENT_TYPE`, `AGENT_DESCRIPTION`, `trace_log`)
4. SYSTEM_PROMPT (if present) — always use this exact structure:
```python
SYSTEM_PROMPT = """
You are <Agent Name> — the <Nth> agent in the LangGraph learning series.
Your purpose: <what this agent demonstrates>.
Concepts you teach: <list of concepts>.
If asked who you are or why you exist — explain exactly this.
Only answer questions related to this agent, its concepts, LangGraph, or the AI Playground Framework we are building.
If the user asks about anything else — politely decline and redirect them to the topics above.
"""
```
5. Each `@tool` function — one at a time
6. `TOOLS` list (if present)
7. LLM instantiation
8. Each node function — one at a time
9. `build_graph()`
10. `_graph = build_graph()` + `run_agent()`

---

## Test Mode — Always Follow When Activated

When the user types **"Test Mode — I want to test 01 Hello Agent"** (using the lab number and name), switch to guided test mode.

**DO NOT teach block by block. DO NOT ask the user to write code.**
Test Mode is for understanding and verifying a finished agent — not building one.

### Step 1 — Read the solution and INSTRUCTIONS before doing anything
- Read `labs/XX-agent-name/solution/xx_agent.py` — the full agent implementation
- Read `labs/XX-agent-name/INSTRUCTIONS.md` — for the test checklist and concept list
- Never generate tests from memory — always derive them from the actual solution file

### Step 2 — Give the Test Checklist
Output the full test checklist in this exact format:

```
### Test Checklist — <Agent Name>
| # | Input | Expected output | Trace expected |
|---|---|---|---|
| 1 | ... | ... | ... |
| 2 | ... | ... | ... |
| 3 | ... | ... | ... |
```

After each row, add a **Why this test** explanation:
> **Why test #1:** This input exercises the `node_classify → tool_call → node_respond` path. Without it, you would never verify that the LLM correctly routes to the tool instead of answering directly.

Always cover:
- The happy path (standard expected usage)
- A path that triggers a tool call (if tools exist)
- A path that does NOT trigger a tool call (if tools exist)
- Each routing branch (if `add_conditional_edges` is used)
- An edge case or boundary input (empty string, unknown intent, etc.)

### Step 3 — Explain every concept used in the agent
After the test checklist, output a **Concept Breakdown** section.

For each concept present in the solution file, explain:
1. **What it is** — one sentence definition, no jargon
2. **Why it was used here** — why this lab uses this concept specifically, not a generic one
3. **What would break without it** — concrete consequence if the developer removed it
4. **How to use it correctly** — one clear rule or pattern to remember

Format:
```
### Concept Breakdown — <Agent Name>

#### <ConceptName> (e.g. ToolNode)
- **What it is:** ...
- **Why used here:** ...
- **What breaks without it:** ...
- **Rule to remember:** ...
```

Include a concept entry for every distinct LangGraph/LangChain/Python construct that appears in the solution:
- Each import that is non-trivial (`ToolNode`, `tools_condition`, `MessagesState`, `SqliteSaver`, `HumanInterrupt`, etc.)
- Each node function
- Each `@tool` function
- The graph structure (edges, conditional edges, loops)
- The `run_agent()` entry point pattern
- Any external service used (Redis, Qdrant, SQLite, etc.)

### Step 4 — Setup instructions (if needed)
If the agent requires infrastructure (Lab 13 = Redis, Lab 10 = Qdrant in-memory, Lab 08 = SQLite), prepend a **Setup** block before the test checklist.

**Always include the exact copy command with full paths** — never say "copy the solution file" without specifying source and destination. Use the Setup section from `labs/XX-agent-name/INSTRUCTIONS.md` as the source of truth for each lab's setup steps.

```
### Setup — <Agent Name>
Before running this agent:
1. Copy the agent file:
   From: `labs/XX-agent-name/solution/xx_agent.py`
   To:   `src/agents/xx_agent.py`
2. <any supporting files — e.g. data/, mixins/>
3. <infrastructure step — e.g. docker compose up -d redis>
4. Start Studio: `python studio.py` → select <Agent Name>
```

### What Test Mode must NOT do
- Never ask the user to write or edit code
- Never give implementation details unless the user asks a follow-up question
- Never skip the Concept Breakdown — it is mandatory in every Test Mode response
- Never copy the concept list from Learn Mode — always derive it from the actual solution file

---

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
| Agent file | `<name>_agent.py` | `hello_agent.py`, `hitl_agent.py` |
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
