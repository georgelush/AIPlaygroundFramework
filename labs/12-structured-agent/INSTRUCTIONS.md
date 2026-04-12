# Agent 12 — Structured Output Agent

## What it demonstrates
**Guaranteed JSON extraction** — instead of asking the LLM to "please return JSON" (which can fail),
we bind a **Pydantic schema directly to the LLM**. It cannot return anything else.
If the output doesn't match the schema, LangChain raises an error before it reaches your code.

## New concepts vs Agent 11 (Streaming Agent)
| | Streaming Agent (Lab 11) | Structured Output Agent (Lab 12) |
|---|---|---|
| Pattern | Token-by-token streaming | Single call, guaranteed JSON |
| Return type | `Generator[str]` — stream of text | `dict` — structured data |
| LLM binding | `llm.stream()` | `llm.with_structured_output(Schema)` |
| Output validation | None — raw text | Pydantic validates every field |
| Use case | Chat, long responses | Data extraction, ETL, CRM |

## LangGraph concepts
- `TypedDict State` with `input` and `profile` fields — no `messages` list
- Single-node graph — `START → extract → END`
- `run_agent()` returns `dict` — **first agent in the series that does not return a string**

## Pydantic + structured output concepts
- **`BaseModel`** — defines the exact JSON schema the LLM must follow
- **`Field(description=...)`** — LLM reads these descriptions as extraction instructions
- **`Optional[type]`** — field can be `None` if not found in the input text
- **`with_structured_output(Schema)`** — binds schema to LLM — output is always a typed object
- **`result.model_dump()`** — converts Pydantic object to plain Python dict

## Why this is better than "please return JSON"

| Approach | What happens when LLM has a bad day |
|---|---|
| `"Return JSON with name, age, city, role"` | LLM returns markdown, extra text, wrong field names — your code crashes |
| `with_structured_output(PersonProfile)` | LangChain enforces the schema — you get a valid `PersonProfile` or a clear error |

**The key insight:** with structured output, you never write JSON parsing code.
You never call `json.loads()`. You never handle `KeyError`. The object arrives ready to use.

## Real-world value — where you actually use this

| Scenario | What the agent receives | What it returns |
|---|---|---|
| CV processing | Free-form resume text | `{"name": ..., "role": ..., "city": ...}` → HR database |
| Email signature parsing | `John Smith \| CTO \| London` | Structured contact → CRM |
| Form extraction | User fills a free-text box | Structured fields → backend API |
| Data migration | Legacy unstructured records | Clean JSON → new database |

---

## Code structure — block by block

### Block 1 — Docstring
```python
"""
Agent 12 — Structured Output Agent
Pattern: Guaranteed JSON extraction using Pydantic + with_structured_output().
Teaches: Pydantic BaseModel, llm.with_structured_output(), typed LLM responses.

Instead of asking the LLM to "please return JSON", we bind a Pydantic schema
directly to the LLM — it cannot return anything else. If the output doesn't
match the schema, LangChain raises an error before it reaches your code.

Flow:
  user text (free form, any language)
    → node_extract: structured LLM extracts fields → PersonProfile (guaranteed JSON)
    → run_agent returns dict — not string
"""
```
─────────────────────────────────────────────────────────────────────────────
- Documents the key difference from all other agents: `run_agent returns dict — not string`
- The Flow is intentionally minimal — one node, no branching, no loop

### Block 2 — Imports
```python
from typing import TypedDict, Optional

from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, START, END

from src.config import LLM_MODEL, LLM_PROXY, LLM_API_KEY, langfuse_handler
```
─────────────────────────────────────────────────────────────────────────────
- `BaseModel`, `Field` — from `pydantic` — define the schema the LLM must follow
- `Optional` — allows fields to be `None` when not found in the input text
- No `fastembed`, no `qdrant`, no `ToolNode` — this agent needs nothing else

### Block 3 — Contract vars
```python
AGENT_NAME = "Structured Output Agent"
AGENT_TYPE = "chat"
AGENT_DESCRIPTION = "Extracts structured data from free-form text using Pydantic schema and with_structured_output(). Returns guaranteed JSON — name, age, city, role."

trace_log: list[dict] = []
```
─────────────────────────────────────────────────────────────────────────────
- `AGENT_TYPE = "chat"` — even though it returns dict, the type describes how you interact with it
- `trace_log: list[dict] = []` — never reassign — always use `.clear()`

### Block 4 — Pydantic model
```python
class PersonProfile(BaseModel):
    name: str = Field(description="Full name of the person")
    age: Optional[int] = Field(description="Age in years as an integer")
    city: Optional[str] = Field(description="City or location mentioned")
    role: Optional[str] = Field(description="Job title, role, or profession")
```
─────────────────────────────────────────────────────────────────────────────
- `name: str` — required, no `Optional` — if name is missing, extraction failed
- `age: Optional[int]` — can be `None` if not mentioned. LLM converts `"thirty-two"` → `32` automatically
- `Field(description=...)` — the LLM reads these descriptions to know what to extract
- Pydantic validates the types — if LLM returns `age: "N/A"`, it gets rejected before reaching your code

### Block 5 — SYSTEM_PROMPT + LLM
```python
SYSTEM_PROMPT = """
You are Structured Output Agent — the twelfth agent in the LangGraph learning series.
Your purpose: extract structured person data from free-form text input.
Concepts you teach: Pydantic BaseModel, with_structured_output(), guaranteed JSON extraction.
If asked who you are or why you exist — explain exactly this.

Extract the following fields from the user's text:
- name: full name of the person (required)
- age: age in years as integer (optional — null if not mentioned)
- city: city or location (optional — null if not mentioned)
- role: job title or profession (optional — null if not mentioned)

If a field is not present in the text, return null for that field.
Do not invent information that is not in the text.
Only process requests that contain person data to extract.
Only answer questions related to this agent, its concepts, LangGraph, or the AI Playground Framework we are building.
If the user asks about anything else — politely decline and redirect them to the topics above.
"""

llm = ChatOpenAI(
    model=LLM_MODEL,
    base_url=LLM_PROXY,
    api_key=LLM_API_KEY,
    temperature=0.0,
)

structured_llm = llm.with_structured_output(PersonProfile)
```
─────────────────────────────────────────────────────────────────────────────
- `temperature=0.0` — data extraction must be deterministic — same text = same output every time
- `llm.with_structured_output(PersonProfile)` — **the key line** — binds the Pydantic schema to the LLM
- `structured_llm.invoke()` returns a `PersonProfile` object directly — not `AIMessage`
- SYSTEM_PROMPT reinforces the schema instructions — tells LLM to use `null` when data is missing

### Block 6 — State + `node_extract`
```python
class State(TypedDict):
    input: str
    profile: dict


def node_extract(state: State) -> dict:
    trace_log.append({
        "type": "node_exec",
        "label": "Extract",
        "from": "user",
        "to": "llm",
        "arrow": "->",
        "content": state["input"][:200],
        "fn": "node_extract",
    })

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=state["input"]),
    ]

    result: PersonProfile = structured_llm.invoke(
        messages, config={"callbacks": [langfuse_handler]}
    )

    profile = result.model_dump()

    trace_log.append({
        "type": "llm_response",
        "label": "Profile",
        "from": "llm",
        "to": "user",
        "arrow": "->",
        "content": str(profile)[:200],
        "fn": "node_extract",
    })

    return {"profile": profile}
```
─────────────────────────────────────────────────────────────────────────────
- State has only 2 fields — `input` (raw text) and `profile` (extracted dict)
- `result: PersonProfile` — type annotation shows what `structured_llm` returns
- `result.model_dump()` — converts the Pydantic object to a plain Python dict
- Do NOT call `response.content` here — `structured_llm` does not return `AIMessage`

### Block 7 — `build_graph()` + `_graph`
```python
def build_graph():
    g = StateGraph(State)
    g.add_node("extract", node_extract)
    g.add_edge(START, "extract")
    g.add_edge("extract", END)
    return g.compile()


_graph = build_graph()
```
─────────────────────────────────────────────────────────────────────────────
- Simplest possible graph: `START → extract → END`
- One node does everything — `with_structured_output` handles validation internally
- No tools, no branching, no loop needed

### Block 8 — `run_agent()`
```python
def run_agent(payload: str) -> dict:
    trace_log.clear()
    result = _graph.invoke({"input": payload, "profile": {}})
    return result["profile"]
```
─────────────────────────────────────────────────────────────────────────────
- Returns `dict` — **not `str`** — this is the only agent in the series that does this
- `"profile": {}` — TypedDict requires all fields at invoke time — `{}` is overwritten by `node_extract`
- Studio UI automatically renders dict as formatted JSON with syntax highlighting

---

## Test Checklist — Structured Output Agent

### Setup
1. Run Studio: `python studio.py`
2. Select **Structured Output Agent**
3. Every run produces exactly **2 trace entries**: `Extract` → `Profile`

---

### Test 1 — Simple list format (smoke test)

**Input:**
```
Andrei Pop, 32 ani, Cluj, Java developer
```

**Expected output:**
```json
{
  "name": "Andrei Pop",
  "age": 32,
  "city": "Cluj",
  "role": "Java developer"
}
```

| What to check | Expected |
|---|---|
| All 4 fields populated | ✅ |
| `age` is integer `32`, not string `"32"` | ✅ |
| Entry #2 (Profile) in trace | Shows full dict |

---

### Test 2 — Natural sentence (real-world format)

**Input:**
```
Hi team, please add this contact to the CRM. John Anderson, Lead Cloud Architect, 41 years old, based in Seattle.
```

**Expected output:**
```json
{
  "name": "John Anderson",
  "age": 41,
  "city": "Seattle",
  "role": "Lead Cloud Architect"
}
```

| What to check | Expected |
|---|---|
| LLM extracts from narrative text, not just lists | ✅ |
| `role` = `"Lead Cloud Architect"` — multi-word role | ✅ |

> **This is the real value** — no regex, no template, no parsing code.

---

### Test 3 — Missing fields → null

**Input:**
```
Hi, I'm Maria. I'm a UX designer based in Paris.
```

**Expected output:**
```json
{
  "name": "Maria",
  "age": null,
  "city": "Paris",
  "role": "UX designer"
}
```

| What to check | Expected |
|---|---|
| `age` = `null` — not invented | ✅ |
| LLM does NOT hallucinate an age | ✅ |

---

### Test 4 — Number written in words

**Input:**
```
My colleague Alex just turned thirty-two and joined as a DevOps engineer in our Bucharest office.
```

**Expected output:**
```json
{
  "name": "Alex",
  "age": 32,
  "city": "Bucharest",
  "role": "DevOps engineer"
}
```

| What to check | Expected |
|---|---|
| `"thirty-two"` converted to `32` automatically | ✅ |
| No code needed for this conversion — LLM handles it | ✅ |

---

### Test 5 — Off-topic (grounding test)

**Input:**
```
What is the capital of France?
```

**Expected:** LLM fills what it can with `null` — observe the behavior.
`name` will likely be `null` or `"N/A"`. This demonstrates the **limitation** of `with_structured_output`:
the schema is always returned — even for off-topic input. The SYSTEM_PROMPT tries to prevent it, but
the schema constraint takes priority.

---

### Trace — what to verify every run

| # | Label | Type | What it shows |
|---|---|---|---|
| 1 | `Extract` | `node_exec` | The raw input text sent to the LLM |
| 2 | `Profile` | `llm_response` | The extracted dict — all 4 fields |

**Always exactly 2 entries** — no tools, no loop, no branching.

---

### Summary — `with_structured_output()` vs "please return JSON"

| | `"Please return JSON"` | `with_structured_output()` |
|---|---|---|
| LLM can add extra text | ✅ yes — breaks parsing | ❌ impossible |
| Wrong field names | ✅ yes — `KeyError` in your code | ❌ schema enforced |
| Number as string | ✅ yes — `"32"` instead of `32` | ❌ Pydantic converts |
| Missing field | ✅ yes — `KeyError` or `None` surprise | ✅ explicit `null` via `Optional` |
| JSON parsing code | Required — `json.loads()`, try/except | Not needed — object arrives ready |
