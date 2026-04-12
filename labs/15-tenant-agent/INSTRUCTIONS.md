# Agent 15 — Multi-Tenant Agent

## What it demonstrates
**Multi-tenancy patterns** — how to serve multiple isolated users from a single agent instance:
- Each user has a **token budget** that cannot be exceeded by others
- Conversations are **namespaced** per user — `user_id:session_id`
- Requests are **blocked before the LLM** if quota is exhausted

## New concepts vs Agent 14 (Secure Agent)
| | Secure Agent (Lab 14) | Multi-Tenant Agent (Lab 15) |
|---|---|---|
| Gate pattern | Prompt injection detection | Quota enforcement |
| State field | `security_error: str \| None` | `quota_error: str \| None` |
| Storage | None | In-memory dict (replace with Redis/PostgreSQL) |
| Context injection | None | Budget info injected into HumanMessage |
| Payload | `{"message": "..."}` | `{"message": "...", "user_id": "...", "session_id": "..."}` |

## Key pattern — Gate Node before LLM
Both Lab 14 and Lab 15 use the same architectural pattern:
```
START → [gate_node] → conditional_edge → [llm_node] → END
                                       ↘ [error_node] → END
```
The gate node sets an error field in State. If set → block. If None → proceed to LLM.
This pattern is reusable for any pre-LLM check: auth, rate limiting, content policy, etc.

## LangGraph concepts
- `TypedDict State` with `messages`, `user_id`, `session_id`, `quota_error: str | None`
- 3-node graph with conditional routing after `node_check_quota`
- `add_conditional_edges("check_quota", route_after_quota)`
- `MemorySaver` checkpointer — compiled with `g.compile(checkpointer=MemorySaver())`
- `thread_id` namespacing via `config={"configurable": {"thread_id": make_thread_id(user_id, session_id)}}`

## Multi-tenancy concepts
- **Budget isolation** — `_tenant_budgets: dict[str, int]` keyed by `user_id`
- **thread_id namespacing** — `make_thread_id(user_id, session_id)` → `"user_42:session_abc"`
- **Context injection** — budget info prepended to HumanMessage so LLM can answer quota questions
- **Token estimation** — `len(response.content) // 4` approximates token count without extra API calls

---

## Graph structure

```
START
  ↓
[node_check_quota]
  ├─ quota_error? YES ──→ [node_quota_exceeded] ──→ END
  └─ quota_error? NO  ──→ [node_llm] ──────────────→ END
```

---

## Code structure — block by block

### Block 1 — Docstring
Explains the three multi-tenancy patterns: budget isolation, namespacing, quota enforcement.

### Block 2 — Imports
No new external dependencies — multi-tenancy is a design pattern, not a library.

### Block 3 — Contract variables
```python
AGENT_NAME = "Multi-Tenant Agent"
AGENT_TYPE = "chat"
AGENT_DESCRIPTION = "..."
trace_log: list[dict] = []
```

### Block 4 — SYSTEM_PROMPT
Includes explicit permission for the LLM to discuss quota/budget when context is injected:
```
If the user asks about their quota or budget — you may answer based on context provided.
```

### Block 5 — Tenant storage + helpers
```python
DEFAULT_BUDGET = 5000  # tokens per user
_tenant_budgets: dict[str, int] = {}  # user_id -> tokens used

def get_tokens_used(user_id: str) -> int: ...
def update_tokens_used(user_id: str, tokens: int) -> None: ...
def is_within_budget(user_id: str) -> bool: ...
def make_thread_id(user_id: str, session_id: str) -> str: ...
```
─────────────────────────────────────────────────────────────────────────────
- Functions abstract the storage layer — replace dict with Redis by changing only these 4 functions
- `_tenant_budgets` with underscore = private module variable — do not access directly

### Block 6 — State + LLM
```python
class State(TypedDict):
    messages: list
    user_id: str
    session_id: str
    quota_error: str | None   # None = within budget, str = blocked

llm = ChatOpenAI(model=LLM_MODEL, base_url=LLM_PROXY, api_key=LLM_API_KEY, temperature=0.7)
```

### Block 7 — Node functions
Three nodes:
- `node_check_quota` — checks budget, sets `quota_error`
- `node_quota_exceeded` — returns error directly, **LLM never called**
- `node_llm` — injects context prefix, calls LLM, estimates and records token usage

### Block 8 — build_graph()
```python
def route_after_quota(state: State) -> str:
    if state["quota_error"]:
        return "quota_exceeded"
    return "llm"

def build_graph():
    g = StateGraph(State)
    g.add_node("check_quota", node_check_quota)
    g.add_node("quota_exceeded", node_quota_exceeded)
    g.add_node("llm", node_llm)
    g.add_edge(START, "check_quota")
    g.add_conditional_edges("check_quota", route_after_quota)
    g.add_edge("llm", END)
    g.add_edge("quota_exceeded", END)
    return g.compile(checkpointer=MemorySaver())

_graph = build_graph()
```
─────────────────────────────────────────────────────────────────────────────
- `MemorySaver` enables LangGraph thread checkpointing — when `thread_id` is passed in `config`, each user gets their own isolated conversation checkpoint in memory

### Block 9 — run_agent()
```python
def run_agent(payload) -> str:
    trace_log.clear()
    if isinstance(payload, dict):
        user_input = payload.get("message", "")
        user_id = payload.get("user_id", "anonymous")
        session_id = payload.get("session_id", "default")
    else:
        user_input = str(payload)
        user_id = "anonymous"
        session_id = "default"

    thread_id = make_thread_id(user_id, session_id)

    trace_log.append({..."content": f"thread_id={thread_id}"})

    result = _graph.invoke(
        {"messages": [user_input], "user_id": user_id, "session_id": session_id, "quota_error": None},
        config={"configurable": {"thread_id": thread_id}},
    )
    last = result["messages"][-1]
    content = last.content if hasattr(last, "content") else str(last.get("content", ""))
    return content or ""
```
─────────────────────────────────────────────────────────────────────────────
- `thread_id = make_thread_id(user_id, session_id)` → `"user_42:session_abc"` — namespaced, so conversations never cross between users or sessions
- `config={"configurable": {"thread_id": thread_id}}` is the LangGraph API for activating the checkpointer for a specific thread
- `user_id` and `session_id` extracted at the system boundary — the only validation point
- Fallback to `"anonymous"` / `"default"` when fields missing — no exception raised
- `hasattr(last, "content")` handles both `AIMessage` (node_llm) and `dict` (node_quota_exceeded)

---

## How to build this agent

### STEP 1 — Create the agent file
Create this file and leave it completely empty:
**Path:** `src/agents/tenant_agent.py`

### STEP 2 — Build in Learn Mode
Type this in GitHub Copilot Chat:
```
Learn Mode — I want to build 15 Tenant Agent
```
Copilot will guide you block by block through the full implementation.

### STEP 3 — Test in Studio
```powershell
python studio.py
```
Select **Multi-Tenant Agent** from the dropdown.

---

## Test Checklist — Multi-Tenant Agent

| # | Input | Expected output | Trace expected |
|---|---|---|---|
| 1 | `{"message": "What is multi-tenancy?", "user_id": "user_42", "session_id": "s1"}` | Informative answer about multi-tenancy | `node_exec` (Thread, `thread_id=user_42:s1`) → `node_exec` (Quota Check, budget ok) → `llm_response` (LLM) |
| 2 | `{"message": "What is my quota?", "user_id": "user_42", "session_id": "s1"}` | Answer mentioning budget info (used/5000) | `node_exec` (Thread) → `node_exec` (Quota Check, context injection visible) → `llm_response` (LLM) |
| 3 | `{"message": "Hello", "user_id": "user_42", "session_id": "s2"}` | Normal answer | `node_exec` (Thread, `thread_id=user_42:s2`) → `node_exec` (Quota Check) → `llm_response` — same user, new session, isolated checkpoint |
| 4 | `{"message": "Hello", "user_id": "user_99", "session_id": "s1"}` | Normal answer | `node_exec` (Thread, `thread_id=user_99:s1`) → `node_exec` (Quota Check) → `llm_response` — separate budget from user_42 |
| 5 | Send 30+ messages with `user_id: "user_42"` until budget exhausted | `"Quota exceeded for user 'user_42'..."` | `node_exec` (Thread) → `node_exec` (Quota Check) → `node_exec` (Quota Exceeded) — no `llm_response` entry |
| 6 | `{"message": "Hello", "user_id": "user_99"}` after user_42 is blocked | Normal response | `node_exec` → `node_exec` (Quota Check, budget ok) → `llm_response` — user_99 unaffected |
| 7 | `"Hello"` (plain string, no user_id) | Normal response | `node_exec` (Thread, `thread_id=anonymous:default`) → `node_exec` → `llm_response` |

**Why test #1:** The baseline smoke test — confirms `user_id` + `session_id` are parsed from the JSON payload and combined into `thread_id=user_42:s1`. The Thread trace entry must show the correct `thread_id` so you know namespacing is working from the first call.

**Why test #2:** Verifies context injection — the agent prepends user budget info to the HumanMessage so the LLM can answer questions like "what is my quota?". Without this, the LLM has no knowledge of per-user state.

**Why test #3 (namespacing):** `user_42:s1` and `user_42:s2` are different thread_ids → different checkpoints in `MemorySaver`. This proves that the same user in a new session starts fresh — they don't inherit the previous session's state. Watch the **Thread** trace entry — it must show the correct `thread_id` for each call.

**Why test #4 (isolation):** `user_99:s1` and `user_42:s1` share the same session name but different user_ids → completely separate threads. This is the core namespacing proof.

**Why test #5:** Verifies quota enforcement — after budget exhaustion, `node_quota_exceeded` must fire and LLM trace entry must NOT appear.

**Why test #6:** This is the critical isolation test — proves that user_42 exhausting their budget has zero effect on user_99.

**Why test #7:** Verifies the fallback path — a plain string without JSON fields falls back to `anonymous:default` thread_id. Without this guard, sending a plain string would raise a `KeyError` on `payload["user_id"]`.

**What to watch in trace for test #5:**
- Only `Thread`, `Quota Check` and `Quota Exceeded` entries — no `LLM` entry

---

## Key rules to remember

1. **Gate node before LLM** — check quota in `node_check_quota`, never inside `node_llm`
2. **`quota_error: None` must be initialized at invoke** — TypedDict has no defaults
3. **Abstract storage behind functions** — `is_within_budget()` not `_tenant_budgets.get()` directly
4. **Context injection** — prepend user context to HumanMessage so LLM can answer tenant questions
5. **Token estimation** — `len(response.content) // 4` is an approximation; use `response.usage_metadata` in production if available
