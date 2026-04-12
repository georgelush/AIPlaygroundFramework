# Agent 19 — Deploy Agent

## What it demonstrates
**How to expose the agent framework as a REST API and connect it to external workflow tools like n8n:**
- **REST introspection** — agent reads its own registry (`META`, `AGENTS`) to report what's available
- **Health check** — verifies the LLM proxy is reachable via `httpx`
- **LangGraph Platform standard** — `POST /agents/{name}/runs` is the official endpoint contract
- **VS Code Dev Tunnels** — expose local `server.py` as a public URL without any cloud deployment
- **n8n HTTP Request** — call any agent from an external workflow automation tool

Pattern: `processor` — no LLM, no graph. Takes a command, reads registry, returns a report.

---

## New concepts vs Agent 18 (Test Agent)

| | Test Agent (Lab 18) | Deploy Agent (Lab 19) |
|---|---|---|
| Purpose | Test all agents internally | Expose agents to external systems |
| LLM | None | None |
| External call | None | `httpx.get` → LLM proxy health |
| Registry access | `pkgutil` + `importlib` | `AGENTS`, `META` direct import |
| Output | Test report | Status / health / info report |
| External integration | None | n8n HTTP Request node |

---

## Key patterns

### REST introspection
```python
from src.registry import AGENTS, META
```
The agent imports the live registry directly. `META` contains `{name: {type, description, module}}` for every loaded agent. The agent reads this at runtime — if a new agent is added to `src/agents/`, the next `status` call shows it automatically.

### `httpx` health check with external service
```python
response = httpx.get(base + "/health/liveliness", timeout=5.0)
```
`httpx` is Python's modern HTTP client. `timeout=5.0` prevents the call from hanging if the proxy is down. `/health/liveliness` is LiteLLM's unauthenticated liveness endpoint — returns `{"status": "alive"}` without requiring an API key.

### LangGraph Platform endpoint standard
```
POST /agents/{agent_name}/runs
Body: {"payload": "your message"}
```
This is the official LangGraph Platform API contract. Any tool compatible with LangGraph Cloud uses this exact pattern. Using it ensures our framework is interoperable.

### VS Code Dev Tunnels
VS Code can expose a local port as a public HTTPS URL via GitHub's tunnel infrastructure. No external tool needed — it's built into VS Code. The tunnel requires a one-time browser confirmation (Microsoft anti-phishing page) — after that, programmatic clients (n8n, curl) need to send the session cookie.

---

## Agent structure

No LangGraph graph — direct function routing:

```
run_agent(payload)
  ├─ "status"  → _cmd_status()   ← registry report
  ├─ "health"  → _cmd_health()   ← LLM proxy + registry check
  ├─ "info"    → _cmd_info()     ← endpoints + n8n setup guide
  └─ other     → COMMANDS help
```

---

## Code structure — block by block

### Block 1 — Docstring
4 patterns: status report, health check, framework info, n8n integration. States processor pattern and new concepts.

### Block 2 — Imports
```python
import httpx
from src.config import LLM_PROXY, LLM_API_KEY
from src.registry import AGENTS, META
```
No LLM imports — this agent makes no LLM calls.

### Block 3 — Contract vars
```python
AGENT_NAME = "Deploy Agent"
AGENT_TYPE = "processor"
AGENT_DESCRIPTION = "..."
trace_log: list[dict] = []
SERVER_PORT = 8080
COMMANDS = """..."""
```

### Block 4 — `_cmd_status()`
Iterates `META.items()`, formats name + type + description per agent. Returns code block string.

### Block 5 — `_cmd_health()`
`httpx.get` to `/health/liveliness` with 5s timeout. Checks registry count. Returns pass/fail per service.

### Block 6 — `_cmd_info()`
Counts agents by type, lists all endpoints, prints full n8n integration guide.

### Block 7 — `run_agent()`
Normalizes command to lowercase, routes to one of 3 functions, populates `trace_log`.

---

## Test Checklist — Deploy Agent

| # | Input | Expected output | Trace expected |
|---|---|---|---|
| 1 | `status` | List of all registered agents with type and description | `node_exec` (Status) — direct call, no LLM |
| 2 | `health` | `llm_proxy = ok` + `registry = ok (N agents loaded)` | `node_exec` (Health) — `httpx` call to LLM proxy, result shows ok/FAIL |
| 3 | `info` | Endpoints list + n8n integration steps | `node_exec` (Info) — static content, no LLM |
| 4 | `hello` | Unknown command message + COMMANDS help | `node_exec` (Unknown Command) — returns help text |

**Why test #1:** Verifies the registry integration — `status` reads `REGISTRY` at runtime, so any agent that fails to load will be missing here. This is the quickest way to detect an import error in a new agent.

**Why test #2:** Verifies `httpx` is installed and LLM proxy is reachable. If proxy is down, you see `FAIL` with the exact error — useful for debugging connectivity in CI/CD.

**Why test #3:** Verifies static deployment info is correct and n8n integration instructions are included. No LLM call — confirms the agent works without any model dependency.

**Why test #4:** Verifies the guard clause — unknown commands return help, not an error. Without this, an unexpected input would fall through to `None` and the agent would crash.

---

## How to build this agent

### STEP 1 — Create the agent file
Create this file and leave it completely empty:
**Path:** `src/agents/deploy_agent.py`

### STEP 2 — Build in Learn Mode
Type this in GitHub Copilot Chat:
```
Learn Mode — I want to build 19 Deploy Agent
```
Copilot will guide you block by block through the full implementation.

### STEP 3 — Install httpx (if not already installed)
```powershell
pip show httpx
# if not found:
pip install httpx
```

### STEP 4 — Test in Studio
```powershell
python studio.py
```
Select **Deploy Agent** → test `status`, `health`, `info`

### Step 4 — Expose via server + Dev Tunnels
```powershell
# Terminal 1
python server.py

# VS Code → Ports tab → Forward Port 8080 → set to Public
# Copy the generated URL
```

### Step 5 — Connect n8n
In n8n, add an **HTTP Request** node:

| Field | Value |
|---|---|
| Method | `POST` |
| URL | `https://<your-tunnel-url>/agents/Deploy Agent/runs` |
| Body | `{"payload": "status"}` |
| Header | `Cookie: tunnel_phishing_protection=<value-from-browser>` |

> **Dev Tunnels cookie:** Open the tunnel URL in browser first → click Continue → open DevTools → Application → Cookies → copy `tunnel_phishing_protection` value → paste in n8n header.

### Step 6 — Verify
Execute the n8n workflow → you should receive:
```json
{
  "agent": "Deploy Agent",
  "result": "```\nREGISTERED AGENTS...",
  "trace_steps": 2
}
```
