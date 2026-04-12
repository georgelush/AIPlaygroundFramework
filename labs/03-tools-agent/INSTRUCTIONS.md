# Agent 3 — Tools Agent

## What it demonstrates
The **ReAct loop** — LLM decides dynamically whether to call a tool or reply directly.
Introduces tool calling, `ToolNode`, and `tools_condition`.

## LangGraph concepts
- `@tool` decorator — defines a callable function the LLM can invoke
- `bind_tools` — attaches tools to the LLM so it knows they exist
- `ToolNode` — prebuilt node that executes whichever tool the LLM requested
- `tools_condition` — prebuilt routing function: routes to `"tools"` if LLM made a tool call, else to `END`
- ReAct loop: `llm → tools → llm → tools → ... → END`

---

## Code structure — bloc by bloc

### Bloc 1 — Imports
```python
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.tools import tool
```
- `ToolNode` and `tools_condition` from `langgraph.prebuilt` — never implement manually

### Bloc 2 — Tool definitions
```python
@tool
def get_current_time() -> str:
    """Returns the current date and time.
    Use this when the user asks what time or date it is."""
    ...

@tool
def calculate(expression: str) -> str:
    """Evaluates a mathematical expression and returns the result.
    Use this when the user asks to calculate or compute something."""
    ...

TOOLS = [get_current_time, calculate]
```
─────────────────────────────────────────────────────────────────────────────
- Docstring is **mandatory** — the LLM reads it to decide when to call the tool
- Tool name becomes the function name — use `verb_noun` pattern
- Return plain strings only — never return objects

### Bloc 3 — LLM with tools bound
```python
llm = ChatOpenAI(model=LLM_MODEL, ...)
llm_with_tools = llm.bind_tools(TOOLS)
```
─────────────────────────────────────────────────────────────────────────────
- `bind_tools` — injects tool schemas into the LLM's system context
- `llm_with_tools` is used in the node, not plain `llm`

### Bloc 4 — node_llm
```python
def node_llm(state: MessagesState) -> dict:
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    response = llm_with_tools.invoke(messages, config={"callbacks": [langfuse_handler]})
    if response.tool_calls:
        # log tool_call trace entry
    else:
        # log llm_response trace entry
    return {"messages": state["messages"] + [response]}
```
─────────────────────────────────────────────────────────────────────────────
- Same node handles both: tool call request AND final text response
- `response.tool_calls` — list of tool calls the LLM wants to make; empty if answering directly

### Bloc 5 — build_graph (ReAct loop)
```python
def build_graph():
    tool_node = ToolNode(TOOLS)
    g = StateGraph(MessagesState)
    g.add_node("llm", node_llm)
    g.add_node("tools", tool_node)
    g.add_node("tool_log", node_tools)
    g.add_edge(START, "llm")
    g.add_conditional_edges("llm", tools_condition)  # → "tools" or END
    g.add_edge("tools", "tool_log")
    g.add_edge("tool_log", "llm")                    # loop back
    return g.compile()
```
─────────────────────────────────────────────────────────────────────────────
- `tools_condition` handles all routing — zero custom logic needed
- Loop: `llm → tools → tool_log → llm` repeats until LLM answers directly

---

## Trace log
| Input type | Steps | Trace entries |
|---|---|---|
| Direct question | 2 | `node_exec` → `llm_response` |
| Tool question | 4+ | `node_exec` → `tool_call` → `tool_result` → `llm_response` |

---

## Test checklist
| Input | Expected output | What to watch in trace |
|---|---|---|
| `"What is 144 / 12?"` | `12` | `tool_call` (blue) → `tool_result` (purple) → `llm_response` |
| `"What time is it?"` | Current time | Same 4-step pattern with `get_current_time` |
| `"Who are you?"` | Explains Tools Agent | Direct: 2 steps only, no tool call |
