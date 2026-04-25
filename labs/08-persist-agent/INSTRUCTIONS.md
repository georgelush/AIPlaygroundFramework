# Agent 8 — Persist Agent

## What it demonstrates
**Persistent conversation memory** — replacing `MemorySaver` (Lab 02, RAM only) with `SqliteSaver` (writes to a `.sqlite` file on disk).
When the server restarts and the same `thread_id` is used, LangGraph reads the full conversation history from `memory.db` and continues exactly where it left off.

## New concepts vs Agent 2 (Chat Agent)
| | Chat Agent (Lab 02) | Persist Agent (Lab 08) |
|---|---|---|
| Pattern | MemorySaver — RAM | SqliteSaver — disk |
| Survives restart | ❌ No | ✅ Yes |
| Setup required | None | `sqlite3.connect()` + path |
| Production ready | No | Single-instance yes |
| `compile()` | `checkpointer=MemorySaver()` | `checkpointer=SqliteSaver(conn)` |

## LangGraph concepts
- `SqliteSaver` — checkpointer that writes every graph state to a `.db` file
- `thread_id` — key that identifies a conversation; same `thread_id` = same history
- `checkpointer=conn` — passed to `g.compile()` — LangGraph handles save/restore automatically
- `SystemMessage` injection guard — prevents duplicate system prompts when history is restored
- `check_same_thread=False` — required because Gradio/FastAPI run on multiple threads

## Dependency
```
pip install langgraph-checkpoint-sqlite
```
Add to `requirements.txt`:
```
langgraph-checkpoint-sqlite
```

---

## Project structure — files for this agent

```
src/
└── agents/
    └── persist_agent.py     ← the agent (registered in Studio)
memory.db                    ← created automatically on first message (add to .gitignore)
```

> `memory.db` is created at the project root on first run.
> Add it to `.gitignore` — never commit conversation history to Git.

---


## How to build this agent

### STEP 1  Create the agent file
Create this file and leave it completely empty:
**Path:** `src/agents/persist_agent.py`

### STEP 2  Build in Learn Mode
Type this in GitHub Copilot Chat:
```
Learn Mode  I want to build 08 Persist Agent
```
Copilot will guide you block by block through each section below.

### STEP 3  Test in Studio
```powershell
python studio.py
```
Select **Persist Agent** from the dropdown.

---

## Code structure — block by block

### Block 1 — Docstring
```python
"""
Agent 8 — Persist Agent
Pattern: SqliteSaver — persistent conversation memory across server restarts.
...
"""
```
─────────────────────────────────────────────────────────────────────────────
- Every agent file starts with a module-level docstring
- Explains pattern, purpose, and concepts

### Block 2 — Imports
```python
import os
import sqlite3
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.checkpoint.sqlite import SqliteSaver
from src.config import LLM_MODEL, LLM_PROXY, LLM_API_KEY, langfuse_handler
```
─────────────────────────────────────────────────────────────────────────────
- `sqlite3` — Python built-in, no extra install needed
- `SqliteSaver` — from `langgraph-checkpoint-sqlite` (separate package, must be installed)
- `MessagesState` — built-in LangGraph state for chat agents

### Block 3 — Contract vars + DB_PATH
```python
AGENT_NAME = "Persist Agent"
AGENT_TYPE = "chat"
AGENT_DESCRIPTION = "Persistent conversation memory using SqliteSaver. History survives server restarts."

trace_log: list[dict] = []

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "memory.db")
```
─────────────────────────────────────────────────────────────────────────────
- `DB_PATH` calculated once at module level — navigates two levels up from `src/agents/` to project root
- `trace_log` — never reassign with `=`, always `.clear()` + `.append()`

### Block 4 — SYSTEM_PROMPT
```python
SYSTEM_PROMPT = """
You are Persist Agent — the 8th agent in the LangGraph learning series.
...
"""
```
─────────────────────────────────────────────────────────────────────────────
- Injected as `SystemMessage` only once per conversation, not on every message
- Guard: `if not any(isinstance(m, SystemMessage) for m in messages)` prevents duplicates

### Block 5 — LLM + node_chat
```python
llm = ChatOpenAI(model=LLM_MODEL, base_url=LLM_PROXY, api_key=LLM_API_KEY, temperature=0.7)

def node_chat(state: MessagesState) -> dict:
    messages = state["messages"]
    if not any(isinstance(m, SystemMessage) for m in messages):
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages
    ...
    return {"messages": state["messages"] + [response]}
```
─────────────────────────────────────────────────────────────────────────────
- `llm` instantiated once at module level — not inside the node function
- `SystemMessage` injection guard — critical when SqliteSaver restores old history
- Returns partial update — only `messages` field, never full state copy

### Block 6 — build_graph()
```python
def build_graph():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    checkpointer = SqliteSaver(conn)
    g = StateGraph(MessagesState)
    g.add_node("chat", node_chat)
    g.add_edge(START, "chat")
    g.add_edge("chat", END)
    return g.compile(checkpointer=checkpointer)

_graph = build_graph()
```
─────────────────────────────────────────────────────────────────────────────
- `sqlite3.connect(..., check_same_thread=False)` — required for multi-threaded servers
- `SqliteSaver(conn)` — wraps the connection into a LangGraph-compatible checkpointer
- `g.compile(checkpointer=checkpointer)` — **the only change vs Lab 02** — everything else is identical
- `_graph = build_graph()` — compiled once at import, reused on every invocation

### Block 7 — run_agent (entry point)
```python
def run_agent(payload) -> str:
    trace_log.clear()
    if isinstance(payload, str):
        user_input = payload
        thread_id = "default"
    else:
        user_input = payload.get("message", "")
        thread_id = payload.get("thread_id", "default")
    ...
    config = {"configurable": {"thread_id": thread_id}}
    result = _graph.invoke({"messages": [HumanMessage(content=user_input)]}, config=config)
    return result["messages"][-1].content or ""
```
─────────────────────────────────────────────────────────────────────────────
- `isinstance(payload, str)` guard — Studio passes a plain string, API passes a dict
- `thread_id` — identifies the conversation; same ID = same history loaded from disk
- `config = {"configurable": {"thread_id": thread_id}}` — how LangGraph knows which checkpoint to load
- Only the new `HumanMessage` is passed — LangGraph appends the full history from SQLite automatically

---

## How to test in Studio

1. Run Studio: `python studio/studio.py`
2. Open **http://127.0.0.1:8000** in your browser
3. Select **Persist Agent** from the dropdown
4. Type your message in the **Message** field — the agent uses a persistent SQLite database
5. The conversation is remembered across **Send** presses within the same session tab
6. To test persistence: tell the agent your name, then ask "What is my name?" — it will remember

## Test Checklist — Persist Agent

| # | Input | Expected output | Trace expected |
|---|---|---|---|
| 1 | `"My name is Andrei"` | Greeting that acknowledges the name | `node_exec` (`messages in history: 2`) → `llm_response` |
| 2 | `"What is my name?"` (same tab, no restart) | Remembers "Andrei" from the previous turn | `node_exec` (`messages in history: 4`) → `llm_response` — history counter grows |
| 3 | Restart Studio → reopen same tab → `"What is my name?"` | Still remembers "Andrei" | `node_exec` (`messages in history: 4`, restored from `memory.db`) → `llm_response` |

**Why test #1:** Confirms the first message is stored in `memory.db` and the history counter starts at 2 (the HumanMessage + AIMessage). If this fails, `SqliteSaver` is not connected to the graph.

**Why test #2:** Verifies in-session memory — the history counter growing from 2 to 4 confirms that `SqliteSaver` accumulates messages across turns within the same tab (same `thread_id`). Without this, the LLM says "I don't know your name."

**Why test #3:** This is the critical persistence test — it proves the checkpoint survives a full server restart. Without `SqliteSaver`, the conversation state is lost on restart and test #3 fails. This is the whole point of Lab 08.

---

## Verify memory.db contents

After sending at least one message, run in terminal:
```powershell
python -c "import sqlite3; conn = sqlite3.connect('memory.db'); print(conn.execute('SELECT thread_id, checkpoint_ns, type FROM checkpoints').fetchall())"
```
You will see all saved conversations — `thread_id`, checkpoint type, and namespace.

## Clean memory.db (fresh start)

Stop Studio first (`Ctrl+C`), then:
```powershell
Remove-Item memory.db
```
On the next message, SqliteSaver recreates the file automatically empty.

---

## .gitignore — mandatory step

Add this to your `.gitignore` **before first commit** — `memory.db` contains user conversation data and must never go to Git:

```
# SQLite persistent memory (contains user conversation data)
memory.db
```

Open `.gitignore` at the project root and add these two lines at the end.
