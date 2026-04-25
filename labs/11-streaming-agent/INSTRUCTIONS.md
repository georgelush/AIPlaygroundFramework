# Agent 11 — Streaming Agent

## What it demonstrates
**Token streaming** — instead of waiting for the full LLM response and returning it all at once,
the agent delivers each token immediately as the LLM generates it.
The result: the chatbox updates live, word by word — exactly like ChatGPT.

## New concepts vs Agent 10 (RAG Agent)
| | RAG Agent (Lab 10) | Streaming Agent (Lab 11) |
|---|---|---|
| Pattern | Retrieve → augment → generate | Direct LLM call with streaming |
| LLM call | `llm.invoke()` — waits for full response | `llm.stream()` — yields tokens one by one |
| `run_agent` return type | `str` | `Generator[str, None, None]` |
| Graph | Two-node StateGraph | No graph — direct call |
| Studio update | Single response at end | Incremental update per token |
| `studio.py` change | None | `chat()` updated to handle generators |

## Core concepts

### `llm.invoke()` vs `llm.stream()`
```python
# invoke — waits for full response, returns string
response = llm.invoke(messages)
return response.content

# stream — returns iterator, yields chunks as they arrive
for chunk in llm.stream(messages):
    yield chunk.content
```

### Python Generator (`yield`)
A generator is a function that uses `yield` instead of `return`.
- `return` — ends the function, sends one value back
- `yield` — suspends the function, sends a value, resumes from the same point next call

```python
# Normal function
def get_text() -> str:
    return "Hello world"          # all at once

# Generator function
def stream_text() -> Generator[str, None, None]:
    yield "Hello"                 # first call gets "Hello"
    yield " "                     # second call gets " "
    yield "world"                 # third call gets "world"
```

### How Studio handles it
`studio.py` detects generators using `inspect.isgenerator()`:
```python
result = run_fn(user_message)

if inspect.isgenerator(result):
    # streaming path — update chatbox token by token
    for token in result:
        partial += token
        new_history[-1]["content"] = partial
        yield "", new_history, build_trace_html(agent_name)
else:
    # normal path — all other agents, unchanged behavior
    reply = result or ""
    ...
```

## Dependencies
No new dependencies — uses only `langchain-openai` already in `requirements.txt`.

## Files for this agent

```
src/
└── agents/
    └── streaming_agent.py     ← the active agent (registered in Studio)

studio.py                      ← updated: import inspect + chat() generator support

labs/11-streaming-agent/
├── INSTRUCTIONS.md            ← this file
└── solution/
    └── streaming_agent.py     ← reference solution
```

---


## How to build this agent

### STEP 1  Create the agent file
Create this file and leave it completely empty:
**Path:** `src/agents/streaming_agent.py`

### STEP 2  Build in Learn Mode
Type this in GitHub Copilot Chat:
```
Learn Mode  I want to build 11 Streaming Agent
```
Copilot will guide you block by block through each section below.

### STEP 3  Test in Studio
```powershell
python studio.py
```
Select **Streaming Agent** from the dropdown.

---

## Code structure — block by block

### Block 1 — Docstring
```python
"""
Agent 11 — Streaming Agent
Pattern: Token streaming — LLM response delivered chunk by chunk.
Teaches: llm.stream(), Python generator (yield), Gradio incremental output.

Flow:
  user input
    → llm.stream(): yields one token at a time
    → run_agent(): yields each chunk to Studio
    → Studio: updates chatbox incrementally — like ChatGPT
"""
```
─────────────────────────────────────────────────────────────────────────────
- The Flow section describes the streaming pipeline end-to-end
- No graph nodes here — this agent has no StateGraph

### Block 2 — Imports
```python
from typing import Generator

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from src.config import LLM_MODEL, LLM_PROXY, LLM_API_KEY, langfuse_handler, get_llm_temperature
```
─────────────────────────────────────────────────────────────────────────────
- `Generator` from `typing` — used to annotate the return type of `run_agent()`
- No `StateGraph`, `START`, `END` — no graph needed for this pattern
- No tools — streaming is about output delivery, not tool execution

### Block 3 — Contract vars
```python
AGENT_NAME = "Streaming Agent"
AGENT_TYPE = "streaming"
AGENT_DESCRIPTION = "Demonstrates token streaming — LLM response delivered chunk by chunk using llm.stream() and Python generators."

trace_log: list[dict] = []
```
─────────────────────────────────────────────────────────────────────────────
- `AGENT_TYPE = "streaming"` — new type, documents the pattern
- `trace_log` — never reassign with `=`, always use `.clear()`

### Block 4 — SYSTEM_PROMPT + LLM
```python
SYSTEM_PROMPT = """
You are Streaming Agent — the eleventh agent in the LangGraph learning series.
Your purpose: demonstrate token streaming — delivering LLM responses chunk by chunk.
Concepts you teach: llm.stream(), Python generators, yield, Gradio incremental output.
If asked who you are or why you exist — explain exactly this.
Only answer questions related to this agent, its concepts, LangGraph, or the AI Playground Framework we are building.
If the user asks about anything else — politely decline and redirect them to the topics above.
"""

llm = ChatOpenAI(
    model=LLM_MODEL,
    base_url=LLM_PROXY,
    api_key=LLM_API_KEY,
    temperature=0.7,
)
```
─────────────────────────────────────────────────────────────────────────────
- `temperature=0.7` — conversational, same as Hello Agent
- LLM instantiated once at module level — not inside `run_agent()`

### Block 5 — `run_agent()` — the streaming generator
```python
def run_agent(payload: str) -> Generator[str, None, None]:
    trace_log.clear()
    trace_log.append({
        "type": "node_exec",
        "label": "User",
        "from": "user",
        "to": "llm",
        "arrow": "->",
        "content": payload[:200],
        "fn": "run_agent",
    })

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=payload),
    ]

    full_response = ""
    for chunk in llm.stream(messages, config={"callbacks": [langfuse_handler]}):
        token = chunk.content or ""
        full_response += token
        yield token

    trace_log.append({
        "type": "llm_response",
        "label": "LLM",
        "from": "llm",
        "to": "user",
        "arrow": "->",
        "content": full_response[:200],
        "model": llm.model_name,
        "temperature": get_llm_temperature(llm, 0.7),
        "fn": "run_agent",
    })
```
─────────────────────────────────────────────────────────────────────────────
- `-> Generator[str, None, None]` — return type annotation: produces strings, no send value, no return value
- `llm.stream()` — returns an iterator of chunks, each with a `.content` attribute
- `yield token` — makes this a generator; Studio receives each token immediately
- `full_response += token` — assembles full text in memory for trace log at the end
- `trace_log.append` is AFTER the for loop — full response only available after streaming completes

---

## studio.py changes

Two changes are required in `studio.py` to support streaming output:

### Change 1 — Add `import inspect`
```python
import gradio as gr
import inspect                   # ← add this line
from src.registry import AGENTS, TRACES, META, reload_registry
```

### Change 2 — Replace `chat()` function
```python
def chat(user_message: str, history: list, agent_name: str):
    if not user_message.strip():
        yield "", history, build_trace_html(agent_name)
        return

    run_fn = AGENTS[agent_name]
    result = run_fn(user_message)

    if inspect.isgenerator(result):
        partial = ""
        new_history = history + [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": ""},
        ]
        for token in result:
            partial += token
            new_history[-1]["content"] = partial
            yield "", new_history, build_trace_html(agent_name)
        yield "", new_history, build_trace_html(agent_name)
    else:
        reply = result or ""
        new_history = history + [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": reply},
        ]
        yield "", new_history, build_trace_html(agent_name)
```
─────────────────────────────────────────────────────────────────────────────
- `inspect.isgenerator(result)` — detects whether `run_agent` returned a generator or a string
- All existing agents return `str` → `isgenerator` returns `False` → unchanged behavior
- Streaming path: updates the last history entry token by token, `yield`s to Gradio each time
- Gradio detects `yield` in `chat()` and enables incremental UI updates automatically

---

## How to test in Studio

1. Run Studio: `python studio/studio.py`
2. Open **http://127.0.0.1:8000** in your browser
3. Select **Streaming Agent** from the dropdown
4. Type your message in the **Message** field and press **Send**
5. Watch the response appear **token by token** in the chat area — this is the streaming effect

## Test Checklist — Streaming Agent

| # | Input | Expected output | Trace expected |
|---|---|---|---|
| 1 | `"Who are you?"` | Identity explanation appears token by token in the chatbox | `node_exec` (User→LLM) → `llm_response` (LLM→user, full assembled text) |
| 2 | `"Explain what yield does in Python"` | Long detailed explanation — streaming clearly visible | `node_exec` → `llm_response` — trace panel updates AFTER streaming completes |
| 3 | `"What is the weather today?"` | Polite refusal, redirects to agent topics | `node_exec` → `llm_response` (2 entries only — no tools, no routing nodes) |

**Why test #1:** Verifies the generator pattern — text must appear progressively, not all at once. Confirms `yield` is not broken and the Gradio UI correctly renders streaming output.

**Why test #2:** A long response makes streaming visually obvious. If the generator is broken (returns all at once), the user sees a blank screen then sudden full text — the whole point of Lab 11 is lost.

**Why test #3:** Verifies the `SYSTEM_PROMPT` restriction works identically to non-streaming agents. Confirms no extra nodes fire when the LLM answers directly — the streaming wrapper must not change agent behaviour.

**What to observe visually:**
- Text appears progressively in the chatbox — not all at once
- Trace panel updates AFTER streaming completes (expected — trace is populated at the end of the generator)
- Switch to Ping Agent or Hello Agent — they work exactly as before (backward-compatible)
