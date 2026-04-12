# Agent 7 — Base Agent

## What it demonstrates
**Production agent architecture** — a `BaseAgent` class built with three reusable mixin classes via multiple inheritance.
Instead of writing all logic in one flat file, each concern lives in its own mixin and is composed into the agent via `class BaseAgent(CostTrackingMixin, LoggingMixin, AuthMixin)`.

## New concepts vs Agent 6 (Supervisor)
| | Supervisor Agent | Base Agent |
|---|---|---|
| Pattern | Multi-agent delegation | Mixin composition |
| Reusability | Copies code per agent | Inherits shared mixins |
| Cost tracking | None | `CostTrackingMixin` — per-call token + $ tracking |
| Logging | `print()` | `LoggingMixin` — structured terminal logs |
| Auth | None | `AuthMixin` — user identity + role |
| `run_agent` input | String | String OR JSON dict (`user_id`, `role`) |

## LangGraph concepts
- `TypedDict` State with extra fields (`user_id`, `role`) beyond messages
- `BaseAgent` as a class — `node_llm` is a method, not a top-level function
- `build_graph(agent)` takes the agent instance as argument — binds `agent.node_llm` as node
- JSON payload parsing in `run_agent` — `json.loads()` fallback for string input

---

## Project structure — files for this agent

```
src/
├── agents/
│   └── base_agent.py        ← the agent (registered in Studio)
└── mixins/
    ├── cost_tracking.py     ← CostTrackingMixin
    ├── logging_mixin.py     ← LoggingMixin
    └── auth_mixin.py        ← AuthMixin
```

> The mixins live in `src/mixins/` and are **shared** across all agents.
> Never copy mixin code into an agent — always import from `src.mixins`.

---

## Code structure — bloc by bloc

### Bloc 1 — Docstring
```python
"""
Agent 7 — Base Agent
Pattern: BaseAgent class with Mixins — CostTrackingMixin, LoggingMixin, AuthMixin.
...
"""
```
─────────────────────────────────────────────────────────────────────────────
- Every agent file starts with a module-level docstring
- Explains pattern, purpose, and concepts — so any dev can understand without reading all code

### Bloc 2 — Imports
```python
from typing import TypedDict
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage
from langgraph.graph import StateGraph, START, END
from src.config import LLM_MODEL, LLM_PROXY, LLM_API_KEY, langfuse_handler
from src.mixins.cost_tracking import CostTrackingMixin
from src.mixins.logging_mixin import LoggingMixin
from src.mixins.auth_mixin import AuthMixin
```
─────────────────────────────────────────────────────────────────────────────
- Always import `START` and `END` — never use string `"__start__"` or `"__end__"`
- Always import from `src.config` — never instantiate `ChatOpenAI` with hardcoded values
- Mixins imported individually from `src.mixins`

### Bloc 3 — Contract vars + trace_log
```python
AGENT_NAME = "Base Agent"
AGENT_TYPE = "chat"
AGENT_DESCRIPTION = "..."

trace_log: list[dict] = []
```
─────────────────────────────────────────────────────────────────────────────
- These 4 vars are **mandatory** for every agent registered in Studio
- `trace_log` must be a module-level list — never reassign, always `.clear()`

### Bloc 4 — SYSTEM_PROMPT
```python
SYSTEM_PROMPT = """
You are Base Agent — the 7th agent in the LangGraph learning series.
...
"""
```
─────────────────────────────────────────────────────────────────────────────
- Module-level constant — defined once, injected as `SystemMessage` in every LLM call
- Always constrain the agent to its own topic domain

### Bloc 5 — State
```python
class State(TypedDict):
    messages: list[BaseMessage]
    user_id: str
    role: str
```
─────────────────────────────────────────────────────────────────────────────
- Extra fields beyond `messages` — `user_id` and `role` flow through the graph
- Nodes return **only the fields they modified** — never the full state

### Bloc 6 — CostTrackingMixin (src/mixins/cost_tracking.py)
```python
class CostTrackingMixin:
    def __init__(self): ...
    def track_usage(self, response, model: str = "") -> dict: ...
    def get_cost_summary(self) -> dict: ...
```
─────────────────────────────────────────────────────────────────────────────
- `track_usage(response, model)` — reads `response.usage_metadata`, calculates cost from `MODEL_PRICES`
- Returns dict: `{"input_tokens": N, "output_tokens": N, "cost_usd": N}`
- Accumulates totals internally for `get_cost_summary()`

### Bloc 7 — LoggingMixin (src/mixins/logging_mixin.py)
```python
class LoggingMixin:
    def log_info(self, message): ...
    def log_warning(self, message): ...
    def log_error(self, message): ...
    def log_step(self, step, detail=""): ...
```
─────────────────────────────────────────────────────────────────────────────
- Uses Python `logging` module — configured in `src/config.py` with `basicConfig`
- `log_step("node_llm", "user=george")` → `[BaseAgent] STEP=node_llm | user=george`
- Automatically prefixes the class name — no need to pass it manually

### Bloc 8 — AuthMixin (src/mixins/auth_mixin.py)
```python
class AuthMixin:
    def __init__(self): ...
    def set_auth_context(self, user_id, role="user"): ...
    def get_user_id(self) -> str: ...
    def is_admin(self) -> bool: ...
    def get_auth_context(self) -> dict: ...
```
─────────────────────────────────────────────────────────────────────────────
- `set_auth_context` is called in `run_agent` before invoking the graph
- `is_admin()` returns `True` if `role == "admin"` — use for access control
- `get_auth_context()` returns `{"user_id": ..., "role": ...}` — useful for logging

### Bloc 9 — BaseAgent class (multiple inheritance)
```python
class BaseAgent(CostTrackingMixin, LoggingMixin, AuthMixin):
    def __init__(self):
        CostTrackingMixin.__init__(self)
        AuthMixin.__init__(self)
        self.llm = ChatOpenAI(...)
```
─────────────────────────────────────────────────────────────────────────────
- Python MRO resolves method calls: looks in `BaseAgent` first, then left-to-right in parents
- `CostTrackingMixin.__init__` and `AuthMixin.__init__` must be called explicitly — they initialize internal state
- `LoggingMixin` has no `__init__` — no need to call it
- `self.llm` — created inside `__init__`, not at module level — each agent run gets a fresh LLM client

### Bloc 10 — node_llm (method on BaseAgent)
```python
def node_llm(self, state: State) -> dict:
    self.log_step("node_llm", f"user={self.get_user_id()}")
    trace_log.append({"type": "node_exec", "label": "node_llm", ...})

    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    response = self.llm.invoke(messages, config={"callbacks": [langfuse_handler]})

    usage = self.track_usage(response, model=LLM_MODEL)
    self.log_info(f"tokens={usage['input_tokens']}+{usage['output_tokens']}")

    trace_log.append({"type": "llm_response", "label": "LLM", ..., "cost": "..."})

    return {"messages": state["messages"] + [response]}
```
─────────────────────────────────────────────────────────────────────────────
- `self.log_step` and `self.track_usage` — inherited from mixins, called via `self`
- `cost` field in trace entry — picked up by Studio and rendered as green badge
- Returns only `{"messages": ...}` — never mutates state in-place

### Bloc 11 — build_graph(agent)
```python
def build_graph(agent: BaseAgent):
    g = StateGraph(State)
    g.add_node("llm", agent.node_llm)
    g.add_edge(START, "llm")
    g.add_edge("llm", END)
    return g.compile()
```
─────────────────────────────────────────────────────────────────────────────
- Takes the `agent` instance as argument — necessary because `node_llm` is a bound method
- Graph is simple: `START → llm → END`
- Called inside `run_agent` — not at module level (agent must be created first)

### Bloc 12 — run_agent (entry point)
```python
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

    trace_log.append({"type": "node_exec", "label": "INPUT", "from": "user", "to": "graph", ...})

    graph = build_graph(agent)
    result = graph.invoke({"messages": [...], "user_id": user_id, "role": role})
    return result["messages"][-1].content or ""
```
─────────────────────────────────────────────────────────────────────────────
- JSON parsing: if user types a JSON string in Studio, `json.loads()` unpacks it automatically
- `trace_log.clear()` — always first line, never reassign the list
- Creates `BaseAgent()` fresh on every call — no shared state between runs
- `set_auth_context` must be called before `build_graph` — the node reads it via `self`

---

## Trace log (always 3 steps)
| Step | Type | Badge | Description |
|---|---|---|---|
| 1 | `node_exec` | cyan INPUT | User message enters graph |
| 2 | `node_exec` | cyan node_llm | `user=X \| role=Y` |
| 3 | `llm_response` | purple LLM + green cost badge | Response + token/cost info |

---

## Test Checklist — Base Agent
| Input | Expected output | What to watch in trace |
|---|---|---|
| `Hi, who are you and what do you demonstrate?` | Agent describes itself — mentions CostTrackingMixin, LoggingMixin, AuthMixin, multiple inheritance | `#01 INPUT` contains your message; `#02 node_llm` shows `user=anonymous \| role=user`; `#03 LLM` has the green cost badge with token counts |
| `What is the weather forecast for tomorrow?` | Politely refuses and redirects to agent topics | Same 3 steps — cost badge appears regardless of response |
| `{"message": "Explain AuthMixin", "user_id": "<your-name>", "role": "admin"}` | Explains AuthMixin in detail | `#02 node_llm` shows `user=<your-name> \| role=admin` — confirms JSON parsing + set_auth_context worked |
