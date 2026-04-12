# Agent 4 — Router Agent

## What it demonstrates
**Conditional branching** — a classifier node reads the input and decides which node runs next.
Different inputs take different paths through the graph.

## LangGraph concepts
- `TypedDict` — custom state with named fields (vs `MessagesState`)
- `add_conditional_edges` — routes to different nodes based on a routing function's return value
- Routing function — returns a node name string; LangGraph follows it
- Multiple terminal nodes — each branch ends at `END` independently
- `temperature=0.3` — low temperature for deterministic classification

---

## Code structure — bloc by bloc

### Bloc 1 — State definition
```python
from typing import TypedDict

class State(TypedDict):
    user_input: str
    route: str
    response: str
```
─────────────────────────────────────────────────────────────────────────────
- Use `TypedDict` when you need named fields beyond a message list
- All fields must be initialized in `run_agent` before invoking the graph
- Nodes return only the fields they changed

### Bloc 2 — node_classify
```python
def node_classify(state: State) -> dict:
    # LLM classifies input into: "question" | "greeting" | "other"
    response = llm.invoke(prompt, config={"callbacks": [langfuse_handler]})
    route = response.content.strip().lower()
    if route not in ("question", "greeting", "other"):
        route = "other"  # fallback — always guard classifier output
    return {"route": route}
```
─────────────────────────────────────────────────────────────────────────────
- Classifier LLM prompt is very constrained — reply with one word only
- Guard clause: if LLM returns unexpected value → fallback to safe default

### Bloc 3 — routing function
```python
def route_by_type(state: State) -> str:
    if state["route"] == "question":
        return "answer_question"
    elif state["route"] == "greeting":
        return "greet"
    return "fallback"
```
─────────────────────────────────────────────────────────────────────────────
- Must return a string that matches a registered node name
- Never return `None` or raise from a routing function

### Bloc 4 — build_graph
```python
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
```
─────────────────────────────────────────────────────────────────────────────
- `add_conditional_edges("classify", route_by_type)` — classify node → routing function → next node
- Each branch node connects directly to `END` — no merge needed

---

## Difference from Agent 3
| | Tools Agent | Router Agent |
|---|---|---|
| Branching based on | Tool calls (LLM decides) | Input classification (LLM classifies) |
| Branch destination | `ToolNode` or `END` | One of 3 response nodes |
| Loop | Yes (ReAct) | No — always 2 nodes |
| State type | `MessagesState` | `TypedDict` |

---

## Trace log (always 2 nodes = 4 trace entries)
| Step | Type | Description |
|---|---|---|
| 1 | `node_exec` | Input enters classify |
| 2 | `node_exec` | Route decision logged |
| 3 | `llm_response` | Answer/Greet/Fallback node responds |

---

## Test checklist
| Input | Route | What to watch in trace |
|---|---|---|
| `"What is LangGraph?"` | `question` → answer_question | Step 2 shows `Routed to: question` |
| `"Hello!"` | `greeting` → greet | Step 2 shows `Routed to: greeting` |
| `"Book me a flight to Paris"` | `other` → fallback | Step 2 shows `Routed to: other` |
