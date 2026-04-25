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


## How to build this agent

### STEP 1  Create the agent file
Create this file and leave it completely empty:
**Path:** `src/agents/supervisor_agent.py`

### STEP 2  Build in Learn Mode
Type this in GitHub Copilot Chat:
```
Learn Mode  I want to build 06 Supervisor Agent
```
Copilot will guide you block by block through each section below.

### STEP 3  Test in Studio
```powershell
python studio.py
```
Select **Supervisor Agent** from the dropdown.

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

## How to test in Studio

1. Run Studio: `python studio/studio.py`
2. Open **http://127.0.0.1:8000** in your browser
3. Select **Supervisor Agent** from the dropdown
4. Type your message in the **Message** field and press **Send**
5. The **Trace** panel shows the delegation path (orange = sub-graph called, yellow = result returned)

## Test Checklist

| # | Input | Expected output | Trace expected |
|---|---|---|---|
| 1 | `"Who are you?"` | Agent introduces itself via the Chat sub-agent | `node_exec` (classify) → `graph_call` (Delegated to: chat, orange) → `graph_result` (chat, yellow) → `llm_response` |
| 2 | `"What is 256 / 16?"` | `16` | `node_exec` (classify) → `graph_call` (Delegated to: tools, orange) → `graph_result` (tools, yellow) → `llm_response` |
| 3 | `"Summarize: The fox jumped over the dog repeatedly."` | Short summary | `node_exec` (classify) → `graph_call` (Delegated to: pipeline, orange) → `graph_result` (pipeline, yellow) → `llm_response` |

**Why test #1:** Verifies the `chat` delegation path and confirms that orange `graph_call` + yellow `graph_result` badge pairs appear in the trace. Without this, you never validate that the supervisor can hand off to a sub-agent and receive its result.

**Why test #2:** Exercises the `tools` delegation path and confirms the math tool executes inside the sub-agent. The numerical answer proves the tool loop inside the Tools Agent ran correctly, not just that delegation was routed.

**Why test #3:** Exercises the `pipeline` path and is the most expensive test — it triggers all 3 pipeline nodes inside the sub-agent. Confirms the supervisor can orchestrate a multi-node sub-graph, not just single-node agents.
