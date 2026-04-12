# Agent 6 — Supervisor Agent

## What it demonstrates
**Multi-agent coordination** — one supervisor LLM reads the input and delegates entirely to a specialized sub-agent.
The supervisor never answers directly — it always routes to another agent.

## LangGraph concepts
- Agent-to-agent calls via `run_agent()`
- `AGENT_MAP` dict — maps string keys to agent modules
- `temperature=0.0` — deterministic routing (supervisor must be predictable)
- Separate `DELEGATE_PROMPT` — different instructions for classification vs conversation
- `graph_call` / `graph_result` trace types — orange and yellow badges in Studio

## Difference from Agent 4 (Router)
| | Router Agent | Supervisor Agent |
|---|---|---|
| Routes to | A node inside the same graph | An entirely separate agent |
| Sub-agent executes | N/A | Calls `target.run_agent(payload)` |
| Result comes from | Same graph's state | External agent's return value |
| Graph complexity | Branching, multiple nodes | Linear: supervise → delegate → END |

---

## Code structure — bloc by bloc

### Bloc 1 — Agent imports
```python
import src.agents.chat_agent as chat_agent
import src.agents.tools_agent as tools_agent
import src.agents.pipeline_agent as pipeline_agent
```
─────────────────────────────────────────────────────────────────────────────
- Import each sub-agent as a module — not its `run_agent` directly
- This gives access to `chat_agent.run_agent(...)` at delegation time

### Bloc 2 — State with 3 fields
```python
class State(TypedDict):
    user_input: str
    delegate: str
    result: str
```
─────────────────────────────────────────────────────────────────────────────
- `user_input` — original message from user, passed unchanged to sub-agent
- `delegate` — set by `node_supervise`: `"chat"` | `"tools"` | `"pipeline"`
- `result` — set by `node_delegate`: the sub-agent's response

### Bloc 3 — Two prompts
```python
SYSTEM_PROMPT = """You are Supervisor Agent..."""

DELEGATE_PROMPT = """You are a supervisor that routes requests...
Reply with ONLY one word — exactly one of: chat, tools, pipeline"""
```
─────────────────────────────────────────────────────────────────────────────
- `SYSTEM_PROMPT` — used if the agent ever talks directly (not in this flow)
- `DELEGATE_PROMPT` — used in `node_supervise` for classification; extremely constrained output

### Bloc 4 — node_supervise
```python
def node_supervise(state: State) -> dict:
    response = llm.invoke(prompt, config={"callbacks": [langfuse_handler]})
    delegate = response.content.strip().lower()
    if delegate not in ("chat", "tools", "pipeline"):
        delegate = "chat"   # fallback
    return {"delegate": delegate}
```
─────────────────────────────────────────────────────────────────────────────
- LLM with `temperature=0.0` — deterministic classification
- Always guard output — fallback to `"chat"` if LLM returns unexpected value
- Returns `{"delegate": delegate}` — the next node reads `state["delegate"]`

### Bloc 5 — AGENT_MAP + node_delegate
```python
AGENT_MAP = {
    "chat": chat_agent,
    "tools": tools_agent,
    "pipeline": pipeline_agent,
}

def node_delegate(state: State) -> dict:
    target = AGENT_MAP[state["delegate"]]
    result = target.run_agent(state["user_input"])
    return {"result": result or ""}
```
─────────────────────────────────────────────────────────────────────────────
- `AGENT_MAP` — dictionary that maps string to agent module
- `target.run_agent(state["user_input"])` — calls the sub-agent as if it were a user request
- The sub-agent runs its own full graph internally, with its own trace_log

### Bloc 6 — build_graph (linear, no branching)
```python
def build_graph():
    g = StateGraph(State)
    g.add_node("supervise", node_supervise)
    g.add_node("delegate", node_delegate)
    g.add_edge(START, "supervise")
    g.add_edge("supervise", "delegate")
    g.add_edge("delegate", END)
    return g.compile()
```
─────────────────────────────────────────────────────────────────────────────
- Graph is linear — no `add_conditional_edges` here
- Routing happens INSIDE `node_delegate` via `AGENT_MAP`, not via graph edges
- This is the key distinction: the graph is simple, the intelligence is in the delegate node

---

## Trace log (always 4 steps)
| Step | Type | Badge color | Description |
|---|---|---|---|
| 1 | `node_exec` | cyan | Input enters supervisor |
| 2 | `node_exec` | cyan | Delegate decision logged (`Delegated to: pipeline`) |
| 3 | `graph_call` | **orange** | Calling sub-agent |
| 4 | `graph_result` | **yellow** | Sub-agent result received |

---

## Test checklist
| Input | Delegated to | What to watch in trace |
|---|---|---|
| `"Who are you?"` | `chat` | Step 2: `Delegated to: chat`, orange+yellow badges |
| `"What is 256 / 16?"` | `tools` | Step 2: `Delegated to: tools`, result contains number |
| `"Summarize: The fox jumped over the dog repeatedly."` | `pipeline` | Step 2: `Delegated to: pipeline`, pipeline's 3 internal steps run |
