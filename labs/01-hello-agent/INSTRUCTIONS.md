# Agent 1 — Hello Agent

## What it demonstrates
The simplest possible agent contract — a direct LLM call with no graph, no nodes, no state.
Everything else in the framework builds on top of this foundation.

## LangGraph concepts
- None — this agent intentionally has no graph
- Teaches: `AGENT_NAME`, `AGENT_TYPE`, `AGENT_DESCRIPTION`, `trace_log`, `run_agent`

## Why no graph?
The graph is not mandatory. When logic is simple and linear (one LLM call, one response),
adding a graph only adds complexity. The agent contract is what matters here.

---


## How to build this agent

### STEP 1  Create the agent file
Create this file and leave it completely empty:
**Path:** `src/agents/hello_agent.py`

### STEP 2  Build in Learn Mode
Type this in GitHub Copilot Chat:
```
Learn Mode  I want to build 01 Hello Agent
```
Copilot will guide you block by block through each section below.

### STEP 3  Test in Studio
```powershell
python studio.py
```
Select **Hello Agent** from the dropdown.

---

## Code structure — bloc by bloc

### Bloc 1 — Imports
```python
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from src.config import LLM_MODEL, LLM_PROXY, LLM_API_KEY, langfuse_handler, get_llm_temperature
```
─────────────────────────────────────────────────────────────────────────────
- `ChatOpenAI` — LangChain wrapper around the LiteLLM proxy
- `HumanMessage` / `SystemMessage` — typed message wrappers (LLM reads role from type)
- `langfuse_handler` — tracing callback, passed to every LLM call

### Bloc 2 — Contract variables
```python
AGENT_NAME = "Hello Agent"
AGENT_TYPE = "chat"
AGENT_DESCRIPTION = "..."
trace_log: list[dict] = []
```
─────────────────────────────────────────────────────────────────────────────
- `AGENT_NAME` — display name in Studio dropdown and API response
- `AGENT_TYPE` — `"chat"` | `"processor"` | `"pipeline"`
- `trace_log` — never reassign, always use `.clear()` — registry holds a reference to this list

### Bloc 3 — SYSTEM_PROMPT
```python
SYSTEM_PROMPT = """
You are Hello Agent — the first agent in the LangGraph learning series.
...
"""
```
─────────────────────────────────────────────────────────────────────────────
- Injected as `SystemMessage` before every request
- Defines agent identity and topic restrictions

### Bloc 4 — LLM instantiation
```python
llm = ChatOpenAI(
    model=LLM_MODEL,
    base_url=LLM_PROXY,
    api_key=LLM_API_KEY,
    temperature=0.7,
)
```
─────────────────────────────────────────────────────────────────────────────
- Always import config values — never hardcode model name or URL in agents
- `temperature=0.7` — creative, conversational responses

### Bloc 5 — run_agent
```python
def run_agent(payload: str) -> str:
    trace_log.clear()
    # log input
    response = llm.invoke(messages, config={"callbacks": [langfuse_handler]})
    # log output
    return response.content or ""
```
─────────────────────────────────────────────────────────────────────────────
- Entry point — called by registry, Studio, and server
- `trace_log.clear()` — always first line, never skip
- `config={"callbacks": [langfuse_handler]}` — always pass, every LLM call

---

## Trace log (2 steps)
| Step | Type | From → To | What you see |
|---|---|---|---|
| 1 | `node_exec` | user → llm | User input |
| 2 | `llm_response` | llm → user | LLM reply + model + temp |

---

## Test Checklist

| # | Input | Expected output | Trace expected |
|---|---|---|---|
| 1 | `"Who are you?"` | Explains it is Hello Agent, first in the LangGraph series | `node_exec` → `llm_response` (2 entries) |
| 2 | `"What is the weather today?"` | Politely declines, redirects to LangGraph topics | `node_exec` → `llm_response` (2 entries, no tool call) |

**Why test #1:** Verifies the agent identity and `SYSTEM_PROMPT` are wired correctly into the graph. Without this test, you would never confirm the LLM actually reads the system instructions and introduces itself as Hello Agent.

**Why test #2:** Verifies the `SYSTEM_PROMPT` topic restriction — the LLM must refuse off-topic questions. This is the key behavioral constraint of Lab 01. If the system prompt is missing or incorrectly placed, the LLM answers weather questions freely.
