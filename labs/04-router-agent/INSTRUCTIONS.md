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


## How to build this agent

### STEP 1  Create the agent file
Create this file and leave it completely empty:
**Path:** `src/agents/router_agent.py`

### STEP 2  Build in Learn Mode
Type this in GitHub Copilot Chat:
```
Learn Mode  I want to build 04 Router Agent
```
Copilot will guide you block by block through each section below.

### STEP 3  Test in Studio
```powershell
python studio.py
```
Select **Router Agent** from the dropdown.

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

## How to test in Studio

1. Run Studio: `python studio/studio.py`
2. Open **http://127.0.0.1:8000** in your browser
3. Select **Router Agent** from the dropdown
4. Type your message in the **Message** field and press **Send**
5. The **Trace** panel shows which branch the router selected (question / greeting / fallback)

## Test Checklist

| # | Input | Expected output | Trace expected |
|---|---|---|---|
| 1 | `"What is LangGraph?"` | Detailed LangGraph explanation | `node_exec` (classify) → `node_exec` (Routed to: question) → `llm_response` (answer_question node) |
| 2 | `"Hello!"` | Friendly greeting | `node_exec` (classify) → `node_exec` (Routed to: greeting) → `llm_response` (greet node) |
| 3 | `"Book me a flight to Paris"` | Polite decline, out-of-scope message | `node_exec` (classify) → `node_exec` (Routed to: other) → `llm_response` (fallback node) |

**Why test #1:** Exercises the `question` branch — `classify` node routes to `answer_question`. Verifies `add_conditional_edges` reads `state["route"]` and follows the correct path. Without this, the routing function is never validated for the main use case.

**Why test #2:** Exercises the `greeting` branch — confirms the classifier distinguishes social input from informational questions. Tests that `route_by_type` returns `"greet"` and the trace badge shows `Routed to: greeting`.

**Why test #3:** Exercises the `other` / fallback branch — the safety net for unrecognised input. Confirms the guard clause (`if route not in ("question", "greeting", "other"): route = "other"`) and fallback node work correctly.
