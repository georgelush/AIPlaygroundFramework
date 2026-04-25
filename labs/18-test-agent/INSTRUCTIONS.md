# Agent 18 — Test Agent

## What it demonstrates
**Automated testing patterns for LangGraph agents** — how to build a test runner that validates every agent in the framework without touching production code:
- **Contract checks** — verify every agent exposes `AGENT_NAME`, `AGENT_TYPE`, `AGENT_DESCRIPTION`, `trace_log`, and `run_agent`
- **Trace assertions** — verify `trace_log` is populated with valid entries after `run_agent()` is called
- **Mock LLM** — replace the real LLM with a `MagicMock` — no API cost, fully deterministic, instant
- **Auto-discovery** — uses `pkgutil` + `importlib` to find and import every agent automatically — no hardcoded list

This agent IS itself a test runner — send `"run tests"` in Studio and it executes the full suite, then prints a structured report per agent.

---

## New concepts vs Agent 17 (Approval Agent)

| | Approval Agent (Lab 17) | Test Agent (Lab 18) |
|---|---|---|
| Agent type | `"chat"` | `"processor"` — first processor in curriculum |
| LLM usage | Yes — classifies sensitivity | No — no LLM needed |
| Agent discovery | None | `pkgutil.iter_modules` + `importlib.import_module` |
| Testing pattern | None | Contract check, trace check, mock LLM check |
| Output format | Conversational string | Structured test report |
| External libs | None new | `unittest.mock` — `MagicMock`, `patch` |

---

## Key patterns

### `AGENT_TYPE = "processor"`
The first agent in the curriculum that is NOT `"chat"`. A processor takes a command and returns a report — it does not have a conversation. No LLM is instantiated inside the agent itself.

### Auto-discovery with `pkgutil`
```python
for finder, module_name, _ in pkgutil.iter_modules(agents_pkg.__path__):
    mod = importlib.import_module(f"src.agents.{module_name}")
```
`pkgutil.iter_modules` scans a package's folder and returns all module names it finds. `importlib.import_module` loads them at runtime. Together they allow the test runner to discover all agents without a hardcoded list — add a new agent file and it is tested automatically.

### `MagicMock` — fake LLM
```python
mock_response = MagicMock()
mock_response.content = "mocked response"

mock_llm = MagicMock()
mock_llm.invoke.return_value = mock_response
mock_llm.bind_tools.return_value = mock_llm
```
`MagicMock` is an object that accepts any method call and returns another `MagicMock` by default. We override `.invoke()` and `.bind_tools()` explicitly so agents that use either pattern work correctly.

### `patch` — dependency injection at test time
```python
with patch("langchain_openai.ChatOpenAI", return_value=mock_llm):
    output = mod.run_agent("test input")
```
`patch` temporarily replaces `ChatOpenAI` with the mock for the duration of the `with` block. Any agent that calls `ChatOpenAI(...)` inside `run_agent()` receives the mock instead of the real class. After the block, the real class is restored automatically.

### Functions as data (iterator pattern)
```python
for check_fn in (_check_contract, _check_trace_log, _check_mock_llm):
    r = check_fn(module_name, mod)
```
Functions are first-class objects in Python. Putting them in a tuple and iterating avoids three separate call lines and makes it trivial to add new checks later.

---

## Graph structure

No LangGraph graph — this agent uses a direct function call pattern:

```
run_agent("run tests")
  ↓
_run_all_checks()
  ↓
_discover_agents()         ← pkgutil scan
  ↓
for each agent:
  _check_contract()        ← contract validation
  _check_trace_log()       ← trace_log assertion
  _check_mock_llm()        ← mock LLM run
  ↓
format report
  ↓
return string
```

---

## Code structure — block by block

### Block 1 — Docstring
Explains the 4 patterns: mock LLM, trace assertions, contract checks, regression suite. States that the agent is itself a test runner.

### Block 2 — Imports
```python
import importlib
import pkgutil
from unittest.mock import MagicMock, patch

import src.agents as agents_pkg
from src.config import LLM_MODEL, LLM_PROXY, LLM_API_KEY, langfuse_handler
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
```
- `importlib` / `pkgutil` — agent auto-discovery
- `MagicMock`, `patch` — mock LLM injection
- `src.agents` — the package whose `__path__` we scan
- LLM imports kept for contract completeness (not used directly)

### Block 3 — Contract vars
```python
AGENT_NAME = "Test Agent"
AGENT_TYPE = "processor"
AGENT_DESCRIPTION = "Runs automated checks against all agents in src/agents/ — contract validation, mock LLM tests, trace assertions."

trace_log: list[dict] = []
```
First agent with `AGENT_TYPE = "processor"`.

### Block 4 — `_discover_agents()`
Scans `src/agents/` using `pkgutil.iter_modules`, imports each module with `importlib.import_module`. Returns list of `(module_name, module)` tuples. If import fails, stores `None` for the module.

### Block 5 — `_check_contract()`
Iterates over the 5 required contract attributes. Returns a result dict with `passed`, `errors` list.

### Block 6 — `_check_trace_log()`
Clears `trace_log`, calls `run_agent("test input")`, verifies log is non-empty and each entry has `type`, `label`, `content` keys.

### Block 7 — `_check_mock_llm()`
Creates `MagicMock` for LLM, patches `ChatOpenAI`, calls `run_agent()`, verifies output is not `None`.

### Block 8 — `_run_all_checks()`
Orchestrates all checks. Iterates agents, runs all 3 checks per agent, counts passed/failed, returns summary dict.

### Block 9 — `run_agent()`
Entry point. Accepts `"run tests"` command only. Calls `_run_all_checks()`, formats report as grouped text per agent, wraps in code block for Studio rendering.

---

## How to test in Studio

1. Run Studio: `python studio/studio.py`
2. Open **http://127.0.0.1:8000** in your browser
3. Select **Test Agent** from the dropdown
4. Type `run tests` in the **Message** field and press **Send**
5. The agent runs a live test suite across all loaded agents and returns a formatted report
6. The report groups results by agent and marks each check as pass or fail

## Test Checklist — Test Agent

| # | Input | Expected output | Trace expected |
|---|---|---|---|
| 1 | `run tests` | Markdown report showing all agents with pass/fail per check | `node_exec` (Test Run Started) → `node_exec` per agent checked → `llm_response` (Report) |
| 2 | `hello` | `"Send 'run tests' to execute the full test suite."` | No trace entries — direct return before any node runs |
| 3 | `RUN TESTS` | Same report as test #1 | Same trace as #1 — case normalisation via `.strip().lower()` |

**Why test #1:** Exercises the full discovery → check → report pipeline. Verifies `_run_all_checks()` runs without error and all existing agents pass.

**Why test #2:** Verifies the guard clause — the agent does nothing for unknown commands, does not crash, returns a helpful hint.

**Why test #3:** Verifies `.strip().lower()` normalization — `"RUN TESTS"` must be treated identically to `"run tests"`.

---

## How to build this agent

### STEP 1 — Create the agent file
Create this file and leave it completely empty:
**Path:** `src/agents/test_agent.py`

### STEP 2 — Build in Learn Mode
Type this in GitHub Copilot Chat:
```
Learn Mode — I want to build 18 Test Agent
```
Copilot will guide you block by block through the full implementation.

### STEP 3 — Test in Studio
```powershell
python studio.py
```
Select **Test Agent** → send: `run tests`
