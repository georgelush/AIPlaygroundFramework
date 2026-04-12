# Agent 9 — HITL Agent

## What it demonstrates
**Human-in-the-Loop execution** — the agent detects sensitive actions (delete, deploy, reset) and **pauses the graph** using `interrupt()` before executing. A human must explicitly approve or reject. The approval gate persists across server restarts via `SqliteSaver`.

## New concepts vs Agent 8 (Persist Agent)
| | Persist Agent (Lab 08) | HITL Agent (Lab 09) |
|---|---|---|
| Pattern | SqliteSaver — persistent memory | interrupt() — approval gate |
| Graph pauses mid-run | ❌ No | ✅ Yes |
| Human decision required | ❌ No | ✅ Yes |
| State stored until decision | RAM (lost on restart) | SqliteSaver (survives restart) |
| Resume mechanism | N/A | `Command(resume=...)` |

## LangGraph concepts
- `interrupt(data)` — pauses the graph mid-node, stores the checkpoint in SQLite, returns `data` to the caller
- `Command(resume=value)` — resumes a suspended graph, passing `value` as the result of `interrupt()`
- `get_state(config)` — checks if a graph is suspended (has pending `next` nodes)
- `state.next` — non-empty tuple means the graph is waiting for a resume signal
- Two-node sequential graph — `detect` runs first as a guard, `chat` runs after if no interrupt occurred

## Why SqliteSaver is required for HITL
Without SqliteSaver, the checkpoint disappears on server restart. The user could send a sensitive request, the server restarts overnight, and `"approve"` the next morning would have no context to resume. With SqliteSaver, the suspended graph lives in `memory.db` — LangGraph restores it automatically regardless of restarts.

## Dependency
```
pip install langgraph-checkpoint-sqlite
```
Already in `requirements.txt`.

---

## Design decision — keywords vs LLM classifier

This lab uses a simple keyword list (`SENSITIVE_KEYWORDS`) to detect sensitive actions:
```python
SENSITIVE_KEYWORDS = ["delete", "remove", "drop", "send", "deploy", "reset", "sterge", "trimite"]
```

**Why keywords here:** Simple, fast, zero extra LLM cost — ideal for teaching the `interrupt()` concept without added complexity.

**In production, use an LLM classifier instead:**
```python
def is_sensitive(user_input: str) -> bool:
    response = llm.invoke([
        SystemMessage(content="Respond only with YES or NO. Is this a sensitive or destructive action?"),
        HumanMessage(content=user_input)
    ])
    return "YES" in response.content.upper()
```
This detects intent regardless of exact wording (`"nuke the db"`, `"wipe everything"`, any language).

---

## Project structure — files for this agent

```
src/
└── agents/
    └── hitl_agent.py     ← the agent (registered in Studio)
memory.db                 ← shared with Lab 08, created automatically
```

---

## Code structure — block by block

### Block 1 — Docstring
```python
"""
Agent 9 — HITL Agent
Pattern: Human-in-the-Loop — interrupt() approval gate before sensitive actions.
...
"""
```
─────────────────────────────────────────────────────────────────────────────
- Documents pattern, purpose, and how to interact with the agent

### Block 2 — Imports
```python
import os
import sqlite3
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.types import interrupt, Command
from langgraph.checkpoint.sqlite import SqliteSaver
from src.config import LLM_MODEL, LLM_PROXY, LLM_API_KEY, langfuse_handler
```
─────────────────────────────────────────────────────────────────────────────
- `interrupt`, `Command` — new in Lab 09, from `langgraph.types`
- `AIMessage` — needed to return approval/rejection messages directly from `node_detect`

### Block 3 — Contract vars + constants
```python
AGENT_NAME = "HITL Agent"
AGENT_TYPE = "chat"
AGENT_DESCRIPTION = "..."
trace_log: list[dict] = []
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "memory.db")
SENSITIVE_KEYWORDS = ["delete", "remove", "drop", "send", "deploy", "reset", "sterge", "trimite"]
```
─────────────────────────────────────────────────────────────────────────────
- `SENSITIVE_KEYWORDS` — single source of truth for detection logic. Add words here, nowhere else.

### Block 4 — SYSTEM_PROMPT
```python
SYSTEM_PROMPT = """
You are HITL Agent — the 9th agent in the LangGraph learning series.
...
"""
```
─────────────────────────────────────────────────────────────────────────────
- Does NOT list sensitive keywords — detection is handled by code, not the LLM
- Tells LLM how to handle the approval flow when invoked

### Block 5 — LLM + node_detect + node_chat

**`node_detect`** — runs first, acts as a guard gate:
```python
def node_detect(state: MessagesState) -> dict:
    last_message = state["messages"][-1].content
    if any(kw in last_message.lower() for kw in SENSITIVE_KEYWORDS):
        decision = interrupt({...})   # graph pauses here
        if str(decision).lower() == "approve":
            return {"messages": [...AIMessage("Approved...")]}
        else:
            return {"messages": [...AIMessage("Rejected...")]}
    return {"messages": state["messages"]}  # no change — pass through
```
─────────────────────────────────────────────────────────────────────────────
- If no sensitive keyword → returns state unchanged, `node_chat` runs next
- If sensitive → `interrupt()` freezes the graph, saves checkpoint to SQLite
- On resume → decision flows back as the return value of `interrupt()`

**`node_chat`** — runs after detect for normal messages:
- Standard LLM call with SystemMessage injection guard
- Only executes if `node_detect` did not interrupt

### Block 6 — build_graph()
```python
def build_graph():
    conn = SqliteSaver(sqlite3.connect(DB_PATH, check_same_thread=False))
    g = StateGraph(MessagesState)
    g.add_node("detect", node_detect)
    g.add_node("chat", node_chat)
    g.add_edge(START, "detect")
    g.add_edge("detect", "chat")
    g.add_edge("chat", END)
    return g.compile(checkpointer=conn)
```
─────────────────────────────────────────────────────────────────────────────
- Graph: `START → detect → chat → END`
- `detect` is the guard — must come before `chat`
- `checkpointer=conn` — enables interrupt persistence

### Block 7 — run_agent()
```python
def run_agent(payload) -> str:
    ...
    state = _graph.get_state(config)
    if state.next:
        result = _graph.invoke(Command(resume=decision), config=config)
    else:
        result = _graph.invoke({"messages": [HumanMessage(...)]}, config=config)
```
─────────────────────────────────────────────────────────────────────────────
- `get_state(config)` — checks if graph is suspended for this `thread_id`
- `state.next` — non-empty = graph is waiting for approval
- Two paths: resume a suspended graph OR start a new invocation

---

## Test Checklist — HITL Agent

| Input | Expected output | What to check in trace |
|---|---|---|
| `"Hello, how do you work?"` | Normal response without approval | `node_detect` without interrupt → `node_chat` with LLM response |
| `"delete all files"` | Agent stops and requests approval | `node_detect` → `HITL` suspended |
| `"approve"` (same tab, no restart) | `"Approved. Executing: delete all files"` | `HITL` with `human decision: approve` |
| `"delete the database"` + restart Studio + `"reject"` | `"Action rejected. Nothing was executed."` | `HITL` with `human decision: reject` — restored from `memory.db` |

---

**Test 1 — Normal flow (no approval)**
1. Start Studio: `python studio.py`
2. Select **HITL Agent**
3. Send `"Hello, how do you work?"`
4. ✅ Direct response — no pause, no approval

---

**Test 2 — Persistence (SqliteSaver + interrupt)**

This is the key test for Lab 09 — verifies that `interrupt()` survives a full server restart:

1. Send `"delete all files"` → the agent stops and requests approval
2. **Stop Studio** (`Ctrl+C`) — simulating a server restart
3. **Restart Studio** (`python studio.py`)
4. Send `"approve"` — **without resubmitting the original request**
5. ✅ Agent responds `"Approved. Executing: delete all files"`

**Why do steps 2-3 (restart) matter?**
Without SqliteSaver, the checkpoint would be lost on restart and `"approve"` would have nothing to resume. With SqliteSaver, the graph is suspended on disk — LangGraph restores it automatically and continues exactly where it stopped. This proves that **HITL without persistence does not make sense in production**.

---

## Add to .gitignore

`memory.db` contains user conversation data — it must not be committed to GitHub.

Add to `.gitignore`:
```
# SQLite persistent memory (contains user conversation data)
memory.db
```
