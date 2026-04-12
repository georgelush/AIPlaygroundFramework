# Agent 17 — Approval Agent

## What it demonstrates
**Approval workflow patterns** — how to build LLM agents that block sensitive operations until a manager signs off:
- **HITL for sensitive operations** — LLM classifies the request; if sensitive, execution is blocked and queued
- **Manager sign-off** — request stays in a pending queue until `approve:ID` or `reject:ID` is received
- **Escalation path** — the agent explains exactly what was blocked, what the Request ID is, and how to proceed

This agent combines patterns from Lab 09 (HITL) and Lab 16 (Auth):
- Like Lab 09: execution is blocked until approval is granted
- Like Lab 16: risk level is determined by action type, not just user role

In a real system, approval requests would be sent via email/Teams/Slack to a manager.
Here we simulate approval with an in-memory pending queue and a special `approve:` command.

---

## New concepts vs Agent 16 (Auth Agent)

| | Auth Agent (Lab 16) | Approval Agent (Lab 17) |
|---|---|---|
| Gate pattern | Role permission check | LLM-based sensitivity classification |
| Block reason | Role not permitted | Action is sensitive, needs sign-off |
| Storage | `_user_roles` dict | `_pending_approvals` queue dict |
| Resume path | None — denied is final | `approve:ID` / `reject:ID` command |
| Graph routing | 2 branches | 3 branches (approve, queue, respond) |
| Extra trace | `audit_log` | `_pending_approvals` in-memory queue |

---

## Key patterns

### LLM as classifier (not chatbot)
`node_classify` sends the user input to the LLM with a strict instruction:
> "Reply with exactly one word: SENSITIVE or SAFE."

The LLM is used as a zero-shot classifier — not to generate a response, but to make a routing decision. `temperature=0` ensures deterministic classification.

### Pending queue + two-turn approval
The approval pattern requires **two separate `run_agent()` calls**:
1. First call: user sends a sensitive request → queued, Request ID returned
2. Second call: manager sends `approve:ID` → operation unblocked and executed

This is different from Lab 09 (`interrupt()`) which pauses the same graph invocation. Here we use an external dict as the "pause" mechanism — simpler and Studio-compatible.

### 3-branch routing
```
START
  ↓
[classify]
  ├─ approve:/reject: ──→ [check_approval] ──→ END
  ├─ is_sensitive=True ──→ [queue] ──────────→ END
  └─ is_sensitive=False ─→ [respond] ─────────→ END
```

The router checks `approve:`/`reject:` FIRST — before checking `is_sensitive` — because the LLM might classify `approve:3f2a1b4c` as SENSITIVE.

---

## Graph structure

```
START
  ↓
[node_classify]  ← LLM call: SENSITIVE or SAFE?
  ├─ approve: or reject: ──→ [node_check_approval] ──→ END
  ├─ is_sensitive = True  ──→ [node_queue] ──────────→ END
  └─ is_sensitive = False ──→ [node_respond] ─────────→ END
```

---

## Code structure — block by block

### Block 1 — Docstring
Explains the 3 concepts: HITL for sensitive ops, manager sign-off, escalation path. References Lab 09 and Lab 16 as predecessors.

### Block 2 — Imports
```python
import uuid                              # generates short random Request IDs
from datetime import datetime, timezone  # UTC timestamps for queued requests
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from typing import TypedDict
from src.config import LLM_MODEL, LLM_PROXY, LLM_API_KEY, langfuse_handler
```

### Block 3 — Contract variables + pending queue
```python
trace_log: list[dict] = []
_pending_approvals: dict[str, dict] = {}  # request_id -> {user_input, timestamp}
```
`_pending_approvals` is module-level — it must survive across multiple `run_agent()` calls. Never clear it in `run_agent()`.

### Block 4 — SYSTEM_PROMPT
Lists the sensitive operation categories the LLM will use when classifying requests.

### Block 5 — LLM
```python
llm = ChatOpenAI(model=LLM_MODEL, base_url=LLM_PROXY, api_key=LLM_API_KEY, temperature=0)
```
`temperature=0` — classification must be deterministic. Same input must always produce the same routing decision.

### Block 6 — State
```python
class State(TypedDict):
    user_input: str
    is_sensitive: bool
    request_id: str
    answer: str
```
No `messages: list` — this agent doesn't need conversation history. Each call is a single-turn classification + action.

### Block 7 — `node_classify`
Sends user input to LLM with: `"Reply with exactly one word: SENSITIVE or SAFE."`. Uses `"SENSITIVE" in verdict` (not `==`) to handle partial matches.

### Block 8 — `node_queue`
- Generates `str(uuid.uuid4())[:8]` — 8-char short ID
- Stores `{user_input, timestamp}` in `_pending_approvals`
- Returns escalation message with code blocks for copy-paste in Studio

### Block 9 — `node_respond`
Safe path — calls LLM normally with SYSTEM_PROMPT + user input. No approval gate.

### Block 10 — `node_check_approval`
Processes `approve:ID` and `reject:ID`:
- `approve:` → `_pending_approvals.pop(ID)` → returns execution confirmation
- `reject:` → `_pending_approvals.pop(ID)` → returns cancellation message
- Unknown ID → returns "not found" message

### Block 11 — `route_input` + `build_graph()`
```python
def route_input(state: State) -> str:
    user_input = state["user_input"].strip()
    if user_input.startswith("approve:") or user_input.startswith("reject:"):
        return "check_approval"
    if state["is_sensitive"]:
        return "queue"
    return "respond"
```
Order matters: check `approve:`/`reject:` FIRST, then `is_sensitive`.

### Block 12 — `run_agent()`
```python
def run_agent(payload) -> str:
    trace_log.clear()
    # JSON parsing for Studio string payloads
    if isinstance(payload, dict):
        user_input = payload.get("message", "")
    else:
        try:
            import json
            data = json.loads(str(payload))
            user_input = data.get("message", str(payload))
        except (json.JSONDecodeError, AttributeError):
            user_input = str(payload)

    result = _graph.invoke({
        "user_input": user_input,
        "is_sensitive": False,
        "request_id": "",
        "answer": "",
    })
    return result["answer"] or ""
```
All State fields must be initialized at invoke — TypedDict has no defaults.

---

## How to build this agent

### STEP 1 — Create the agent file
Create this file and leave it completely empty:
**Path:** `src/agents/approval_agent.py`

### STEP 2 — Build in Learn Mode
Type this in GitHub Copilot Chat:
```
Learn Mode — I want to build 17 Approval Agent
```
Copilot will guide you block by block through the full implementation.

### STEP 3 — Test in Studio
```powershell
python studio.py
```
Select **Approval Agent** from the dropdown.

---

## Test Checklist — Approval Agent

| # | Input | Expected output | Trace expected |
|---|---|---|---|
| 1 | `What is an approval workflow?` | Informative LLM answer | `node_exec` (Classify) → `node_exec` (Classify Result: SAFE) → `node_exec` (Respond) → `llm_response` (LLM) |
| 2 | `delete all users from the database` | Request ID + approve/reject code blocks | `node_exec` (Classify) → `node_exec` (Classify Result: SENSITIVE) → `node_exec` (Queue) — no `llm_response` |
| 3 | `approve:XXXXXXXX` (ID from test #2) | `Request XXXXXXXX approved. [SIMULATED] Operation completed.` | `node_exec` (Classify) → `node_exec` (check_approval) → `node_exec` (Approved) → `llm_response` |
| 4 | `delete all users from the database` (again) | New Request ID | `node_exec` (Classify) → `node_exec` (Classify Result: SENSITIVE) → `node_exec` (Queue) — new UUID generated |
| 5 | `reject:XXXXXXXX` (ID from test #4) | `Request XXXXXXXX rejected. Operation cancelled.` | `node_exec` (Classify) → `node_exec` (check_approval) → `node_exec` (Rejected) |
| 6 | `approve:00000000` (fake ID) | `Request ID not found or already processed.` | `node_exec` (Classify) → `node_exec` (check_approval — ID not found) — no `Approved` entry |
| 7 | `transfer 10000 EUR to account 1234` | Request ID + approve/reject code blocks | `node_exec` (Classify) → `node_exec` (Classify Result: SENSITIVE) → `node_exec` (Queue) — financial action flagged |

**Why test #1:** Verifies the SAFE path — benign questions go through `node_respond` and call the LLM normally. Without this, you never confirm the non-sensitive path works.

**Why test #2 (HITL block):** Verifies that `node_queue` fires and `node_respond` does NOT. Watch the trace — there must be NO `LLM Response` entry, only `Classify`, `Classify Result`, and `Queue`.

**Why test #3 (manager sign-off):** This is the core of the pattern — proves that `approve:ID` correctly unblocks the operation. The `Approved` trace entry must appear.

**Why test #4:** Verifies a second sensitive request generates a new UUID. Confirms `_pending_approvals` is not cleared between calls and can hold multiple requests simultaneously.

**Why test #5:** Verifies the reject path — the operation is cancelled cleanly. Confirms `pop()` removes the ID from the queue so it cannot be approved later.

**Why test #6 (unknown ID):** Verifies error handling — the queue is checked before any action. Protects against replay attacks with fake or already-processed IDs.

**Why test #7:** Confirms financial actions are classified as SENSITIVE, not SAFE. The LLM classifier must recognise financial keywords — without this, money transfers would bypass the approval gate.

**What to watch in trace for test #2:**
```
Classify        → user_input content
Classify Result → "SENSITIVE"
Queue           → request_id=XXXXXXXX
```
No `Respond` or `LLM` entry — proves LLM was never called for the sensitive action.

**What to watch in trace for test #3:**
```
Classify        → "approve:XXXXXXXX"
Classify Result → (may say SAFE or SENSITIVE — doesn't matter)
Approved        → request_id=XXXXXXXX | original action
```

---

## Key rules to remember

1. **LLM as classifier** — use `temperature=0` for all classification nodes
2. **Check `approve:`/`reject:` before `is_sensitive`** — routing order prevents misclassification
3. **`_pending_approvals` never cleared in `run_agent()`** — it must persist across calls
4. **`pop()` not `get()` + `del`** — removes from queue atomically
5. **All State fields initialized at invoke** — TypedDict has no defaults, missing fields cause `KeyError`
