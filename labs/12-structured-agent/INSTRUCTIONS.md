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


## How to build this agent

### STEP 1  Create the agent file
Create this file and leave it completely empty:
**Path:** `src/agents/structured_agent.py`

### STEP 2  Build in Learn Mode
Type this in GitHub Copilot Chat:
```
Learn Mode  I want to build 12 Structured Agent
```
Copilot will guide you block by block through each section below.

### STEP 3  Test in Studio
```powershell
python studio.py
```
Select **Structured Agent** from the dropdown.

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

| # | Input | Expected output | Trace expected |
|---|---|---|---|
| 1 | `"Andrei Pop, 32 ani, Cluj, Java developer"` | `{"name": "Andrei Pop", "age": 32, "city": "Cluj", "role": "Java developer"}` | `node_exec` (Extract) → `llm_response` (Profile, `age` is integer 32 not string) |
| 2 | `"Hi team, add John Anderson, Lead Cloud Architect, 41 years old, Seattle."` | `{"name": "John Anderson", "age": 41, "city": "Seattle", "role": "Lead Cloud Architect"}` | `node_exec` (Extract) → `llm_response` (Profile, multi-word role extracted correctly) |
| 3 | `"Hi, I'm Maria. I'm a UX designer based in Paris."` | `{"name": "Maria", "age": null, "city": "Paris", "role": "UX designer"}` | `node_exec` (Extract) → `llm_response` (Profile, `age: null` — LLM does not hallucinate) |
| 4 | `"Alex just turned thirty-two and joined as a DevOps engineer in Bucharest."` | `{"name": "Alex", "age": 32, "city": "Bucharest", "role": "DevOps engineer"}` | `node_exec` (Extract) → `llm_response` (Profile, `"thirty-two"` → `32` automatic conversion) |
| 5 | `"What is the capital of France?"` | JSON response with `null` for most fields — schema always returned | `node_exec` (Extract) → `llm_response` (Profile — off-topic: schema constraint wins over SYSTEM_PROMPT) |

**Why test #1:** The smoke test — confirms `with_structured_output()` binds the `PersonProfile` schema correctly and Pydantic type coercion fires (`age` arrives as integer, not string `"32"`).

**Why test #2:** Tests NLP extraction from a narrative sentence — no commas, no template. The LLM extracts all 4 fields including a multi-word role. Validates that `with_structured_output` works with free-text, not just structured input.

**Why test #3:** Verifies `Optional[int]` — the missing field must be `null`, not invented. Without `Optional`, Pydantic raises a validation error instead of returning `null`.

**Why test #4:** Tests automatic type conversion — "thirty-two" (string) → `32` (int). No code was written for this; the LLM handles number normalisation as part of structured extraction.

**Why test #5:** Demonstrates the schema's limitation — `with_structured_output()` always returns the full schema shape even for off-topic input. The SYSTEM_PROMPT tries to prevent it but the schema constraint takes priority.

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
