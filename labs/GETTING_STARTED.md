# AI Playground Framework — Onboarding Guide
> Everything a new team member needs to get started, contribute, and learn.

---

## 1. What Is This Project?

This is a **LangGraph agent framework** — a platform for building, testing, and deploying AI agents. It has four main components:

- **`studio.py`** — local debug UI (Gradio) — run it to test agents visually
- **`server.py`** — REST API server (FastAPI) — used by n8n and other systems
- **`src/agents/`** — all agents live here — each file is one agent
- **`src/LEARN.md`** — this file — start here

The framework auto-discovers agents — drop a new file in `src/agents/` and it appears in the UI automatically.

---

## 2. First Time Machine Setup (Windows)

> Run all commands below in **PowerShell or CMD as Administrator** (right-click → "Run as administrator").
> After installing Python and Git, **close and reopen** your terminal so the system recognizes the new commands.

---

### 2.1 — Install Required Software

Run each command one by one:

| Program | Install Command |
|---|---|
| Python 3.12 | `winget install -e --id Python.Python.3.12` |
| Git | `winget install -e --id Git.Git` |
| VS Code | `winget install -e --id Microsoft.VisualStudioCode` |
| uv (fast Python package manager) | `powershell -c "irm https://astral.sh/uv/install.ps1 \| iex"` |

Verify everything installed correctly:

```powershell
python --version   # should show 3.12.x
git --version      # should show 2.x.x
code --version     # should show VS Code version
uv --version       # should show uv version
```

---

### 2.2 — Install VS Code Extensions

Run this single command to install all required extensions at once:

```powershell
code --install-extension github.copilot --install-extension github.copilot-chat --install-extension ms-python.python --install-extension ms-python.vscodepylance --install-extension charliermarsh.ruff --install-extension redhat.vscode-yaml --install-extension eamodio.gitlens
```

Or install them one by one:

| Extension | Install Command |
|---|---|
| GitHub Copilot | `code --install-extension github.copilot` |
| GitHub Copilot Chat | `code --install-extension github.copilot-chat` |
| Python | `code --install-extension ms-python.python` |
| Pylance | `code --install-extension ms-python.vscodepylance` |
| Ruff | `code --install-extension charliermarsh.ruff` |
| YAML | `code --install-extension redhat.vscode-yaml` |
| GitLens | `code --install-extension eamodio.gitlens` |

> **Notes:**
> - **Restart Terminal** after installing Python and Git — close and reopen so the PATH is updated.
> - **Git Credential Manager** is installed automatically with Git — no separate command needed.
> - If `winget` is not available, update Windows or install it from the Microsoft Store.

---

## 3. Prerequisites

Before you continue, confirm you have:

| Tool | Version | How to check | How to install |
|---|---|---|---|
| Python | 3.12+ | `python --version` | See **Section 2** above |
| Git | any | `git --version` | See **Section 2** above |
| VS Code | any | `code --version` | See **Section 2** above |
| GitHub account + org access | — | ask the owner | See **Step 0** below |
| `.env` file with credentials | — | ask the owner | provided by owner |

---

## 4. Getting Started (First Time Setup)

> **Where to run these commands?**
> - **Steps 0–1** → open a standard terminal: `cmd.exe` or `PowerShell` (Windows) / `Terminal` (Mac/Linux)
> - **Step 2** → same terminal, **inside the cloned folder** — run the setup script
> - **Step 3** → VS Code opens automatically at the end of setup — use the **integrated terminal** inside VS Code (`Ctrl+` `` ` `` or `View → Terminal`)

---

### Step 0 — Before you clone: get access and install Git (first time only)

Do these two things **before touching the terminal** — they take 5 minutes and are required for Step 1.

---

#### 0.1 — Get a GitHub Personal Access Token (PAT)

You need a token to clone private repositories. Your GitHub password will **not** work.

> Do this in your **browser** — no terminal needed.

1. Log in to [github.com](https://github.com)
2. Click your avatar (top-right) → **Settings**
3. Scroll down → **Developer settings** (bottom-left)
4. **Personal access tokens** → **Tokens (classic)**
5. Click **Generate new token (classic)**
6. Give it a name (e.g. `ai-playground`)
7. Check the **`repo`** scope (full control of private repositories)
8. Click **Generate token**
9. **Copy the token immediately** — you will not see it again. Save it somewhere safe (e.g. Notepad).

> ⚠️ Also ask the project owner to add your GitHub account to the repository organization on GitHub — without this, even a valid token cannot clone the repo.

---

#### 0.2 — Install Git

> Skip this if `git --version` already works in your terminal.

Open **PowerShell or CMD as Administrator** (right-click → "Run as administrator") and run:

```powershell
# Check if Git is already installed
git --version

# If you see 'git is not recognized', install it:
winget install --id Git.Git -e --source winget
```

> After installation, **close and reopen** your terminal, then verify with `git --version`.

---

### Step 1 — Clone the repository
> Run in **CMD / PowerShell / Terminal**

First, navigate to the folder where you want to place the project. A good default is your `Downloads` folder:

```powershell
# Navigate to Downloads (or any folder you prefer)
cd C:\Users\<YOUR_USERNAME>\Downloads
```

> **Why?** The clone command will create a new subfolder here. You need write access to the folder — avoid system folders like `C:\Windows` or `C:\Program Files`.

Then clone using your token directly in the URL — no username needed:

```powershell
git clone https://<YOUR_TOKEN>@github.com/<ORG>/<REPO_NAME>
cd <REPO_NAME>
```

Replace `<YOUR_TOKEN>` with the token you copied in Step 0.2.

Example:
```powershell
git clone https://YOUR_PERSONAL_ACCESS_TOKEN_HERE@github.com/<ORG>/<REPO_NAME>
cd <REPO_NAME>
```

> To avoid typing the token every time, save it in Git's credential manager:
> ```powershell
> git config --global credential.helper manager
> ```

---

### Step 2 — Run the setup script

> ⚠️ **Do NOT double-click `setup.ps1`** — Windows opens it in Notepad.
> ⚠️ **Do NOT use CMD (Command Prompt)** — `.ps1` scripts do not run in CMD. You must use **PowerShell**.

**Windows — open PowerShell:**

Press `Win + R`, type `powershell`, press Enter. Then:

```powershell
cd C:\Users\<YOUR_USERNAME>\Downloads\<REPO_NAME>
.\setup.ps1
```

> **Already in CMD by mistake?** Type `powershell` to switch, then run `.\setup.ps1`.

> If you see *"running scripts is disabled"*, run this once first, then retry:
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

**Mac / Linux — open Terminal:**
```bash
cd ~/Downloads/<REPO_NAME>
chmod +x setup.sh && ./setup.sh
```

The script will automatically:
- Create the virtual environment (`.venv`)
- Install all dependencies from `requirements.txt`
- Create `.env` from the template and **prompt you for credentials interactively**
- Verify everything is working

> ⚠️ You need the credentials **before** running the script — ask the project owner for `LLM_API_KEY`, `LLM_PROXY`, and the Langfuse keys.

---

#### What credentials do I need?

**Option A — Company LiteLLM proxy (recommended for team members)**

Ask the project owner for all values:

| Variable | What it is |
|---|---|
| `LLM_API_KEY` | Authentication key for the LiteLLM proxy |
| `LLM_PROXY` | URL of the LiteLLM proxy server |
| `LLM_MODEL` | Leave as `gpt-5.4-nano` — already set |
| `LANGFUSE_PROXY` | URL of the Langfuse tracing server |
| `LANGFUSE_PUBLIC_KEY` | Langfuse public key |
| `LANGFUSE_SECRET_KEY` | Langfuse secret key |

**Option B — Your own API key (learning on your own)**

If you don't have access to the company proxy, use any OpenAI-compatible provider:

| Provider | Where to get a key |
|---|---|
| OpenAI (GPT-4o) | [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys) |
| Groq (fast + free tier) | [https://console.groq.com](https://console.groq.com) |
| Mistral | [https://console.mistral.ai](https://console.mistral.ai) |
| Ollama (local, free) | No key needed — runs on your machine |

Set `LLM_API_KEY` to your key, `LLM_PROXY` to the provider's base URL, `LLM_MODEL` to the model name (e.g. `gpt-4o`). Leave `LANGFUSE_*` empty — Langfuse is optional.

> ⚠️ The `.env` file contains secrets. It is listed in `.gitignore` and **must never be pushed to GitHub**.

> **Need to update credentials later?** Edit `.env` directly:
> ```powershell
> code .env
> ```

---

### Step 3 — Open the project in VS Code and run the debug UI
> Run in the **VS Code integrated terminal** (`Ctrl+` `` ` `` → `Terminal → New Terminal`)

```bash
# Make sure the virtual environment is active — you should see (.venv) in the prompt
# If not, activate it first:
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Mac / Linux

# Then start the Studio UI:
python studio.py
```

Open your browser at **http://localhost:8000** — the Agent Studio will load automatically.

> **Agent auto-discovery with Reload:**
> The Studio detects agents from `src/agents/` automatically.
> - **Add** a new agent file → click the **Reload** button in the Studio UI — the new agent appears instantly in the dropdown, no restart needed.
> - **Delete** an agent file → click **Reload** — it disappears from the UI immediately.
> You never need to restart `studio.py` when adding or removing agents.

---

## 5. Git Workflow

Branch protection is active — **no one can push directly to `main`**, including the owner.
Every change goes through a Pull Request.

### For developers — your job ends at step 6

```bash
# Step 1 — First time only: already done in Getting Started above

# Step 2 — Every morning: get the latest changes
git checkout main
git pull

# Step 3 — See all branches and switch to your working branch
git branch -a                         # list all local and remote branches
git checkout your-branch-name         # switch to existing branch
git checkout -b your-branch-name      # create new branch AND switch to it
# Example: git checkout -b

# Step 4 — Write your code in VS Code

# Step 5 — Always check status before staging
git status                                         # see what changed — do this BEFORE git add

# Step 6 — Stage and commit
git add .                                          # or specific file: src/agents/agent_tools.py
git commit -m "add example_agent.py — ReAct loop"

# Step 7 — Push and open a Pull Request
git push origin your-branch-name
# Go to GitHub → Compare & pull request → fill in title → Create pull request
# Done — wait for the owner to review and approve
```

### For the owner — reviewing and merging

```bash
# On GitHub:
# Pull requests → open the PR → Files changed tab (review the diff)
# Bypass rules and merge  ← click when approved

# Back in terminal — sync your local main after merge:
git checkout main
git pull
```

### Commit Message Convention

Use the format: `<verb> <what> — <short detail>`

| Verb | When to use | Example |
|---|---|---|
| `add` | new file or feature | `add router_agent.py — conditional branching` |
| `fix` | bug fix | `fix None guard in run_agent` |
| `update` | change to existing file | `update LEARN.md — add git status step` |
| `remove` | delete something | `remove debug print from tools_agent.py` |

Rules:
- Imperative tense — "add", not "added" or "adding"
- English only — no Romanian, no diacritics
- No "I did...", no "fixed the thing", no vague messages like "fix" or "update"
- One commit = one logical change — do not bundle unrelated changes
### What Never Gets Committed (.gitignore)

| Entry | Why |
|---|---|
| `.env` | Contains API keys and secrets — never expose these |
| `.venv/` | Virtual environment — each developer installs their own |
| `__pycache__/` | Auto-generated bytecode — not needed in repo |
| `*.db` | Local SQLite databases |
| `.langgraph_api/` | Local LangGraph Studio checkpoints — not part of this project |

### Common Mistakes

| Mistake | What happens | Fix |
|---|---|---|
| Commit `.env` | API keys exposed publicly | Add `.env` to `.gitignore` immediately |
| Work directly on `main` | Branch protection blocks it | Always create a branch first |
| Vague commit message `"fix"` | Nobody knows what changed | Write what exactly changed |
| `git push --force` | Overwrites others' work | Never use this |

---

## 6. Project Structure

```
Agentic-AI-Playground/
├── src/
│   ├── agents/          # Active agents — auto-loaded by registry
│   │   └── ping_agent.py
│   ├── graphs/          # StateGraph definitions (shared graphs)
│   ├── nodes/           # Reusable node functions
│   ├── tools/           # Reusable @tool functions
│   ├── mixins/          # Reusable mixins (CostTrackingMixin, LoggingMixin, AuthMixin)
│   ├── config.py        # LLM client, Langfuse handler, env vars
│   └── registry.py      # Agent auto-discovery
├── labs/                # 20-lab curriculum (01–17 ✅  |  18–20 🔜)
│   ├── README.md        # Curriculum overview + standards
│   ├── GETTING_STARTED.md  # This file — full setup + framework walkthrough
│   ├── 01-hello-agent/  # ✅ Direct LLM call, agent contract
│   ├── 02-chat-agent/   # ✅ StateGraph, MemorySaver, thread_id
│   ├── 03-tools-agent/  # ✅ ReAct loop, @tool, ToolNode
│   ├── 04-router-agent/ # ✅ Conditional branching, add_conditional_edges
│   ├── 05-pipeline-agent/ # ✅ Sequential nodes, per-node model assignment
│   ├── 06-supervisor-agent/ # ✅ Multi-agent coordination, AGENT_MAP
│   ├── 07-base-agent/   # ✅ BaseAgent + Mixins
│   ├── 08-persist-agent/ # ✅ SqliteSaver, persistent memory
│   ├── 09-hitl-agent/   # ✅ interrupt(), approval gate
│   ├── 10-rag-agent/    # ✅ RAG pipeline, Qdrant in-memory, text-embedding-3-small (multilingual)
│   ├── 11-streaming-agent/ # ✅ llm.stream(), Generator, yield, Gradio incremental output
│   ├── 12-structured-agent/ # ✅ Pydantic, with_structured_output(), guaranteed JSON
│   ├── 13-async-agent/  # ✅ Async + polling, job_id, ainvoke(), Redis TTL, webhook
│   ├── 14-secure-agent/ # ✅ Prompt injection detection, input validation, output sanitization
│   ├── 15-tenant-agent/ # ✅ Budget isolation, thread_id namespacing, quota enforcement
│   ├── 16-auth-agent/   # ✅ RBAC, identity context, audit trail
│   ├── 17-approval-agent/ # ✅ HITL for sensitive operations, manager sign-off, escalation path
│   └── 18–20/           # 🔜 Testing, Deploy, Capstone
├── tests/
├── studio.py            # Gradio debug UI (port 8000)
├── server.py            # FastAPI REST server (port 8080)
├── .env.example
└── requirements.txt
│
├── .env             # Your credentials (LLM key, Langfuse key) — NEVER commit this
├── .env.example     # Template with empty values — safe to commit, shows what's needed
└── .gitignore       # Tells Git what files to NEVER commit
                     # Includes: .env, .venv/, __pycache__/, .langgraph_api/
                     # Rule: if it contains secrets or can be regenerated → add it here
```

---

## 7. Agent Contract

Every file in `src/agents/` **must** have these five things to be auto-registered:

```python
AGENT_NAME = "My Agent"              # English, Title Case — shown in UI and API
AGENT_TYPE = "chat"                  # "chat" | "processor" | "pipeline"
AGENT_DESCRIPTION = "Does X and Y"  # shown in GET /agents

trace_log: list[dict] = []           # NEVER reassign — always use .clear()

def run_agent(payload) -> str | dict:
    trace_log.clear()
    # ... logic here
    return result
```

If any of these are missing, the agent will **not** appear in `studio.py` or `server.py`.

---

## 8. Curriculum — 19 Learning Agents

Each agent teaches exactly one new concept. No business logic — pure learning.

### Layer 1 — Fundamentals

| # | File | Pattern | New Concepts |
|---|---|---|---|
| 1 | `hello_agent.py` | Simple LLM, no graph | Agent contract, trace_log, run_agent |
| 2 | `chat_agent.py` | Single-node StateGraph | StateGraph, START, END, MessagesState, MemorySaver, thread_id |
| 3 | `tools_agent.py` | ReAct loop | @tool, ToolNode, tools_condition, tool calling cycle |
| 4 | `router_agent.py` | Branching | add_conditional_edges, routing functions |
| 5 | `pipeline_agent.py` | Nodes in series | Multiple nodes, extra state fields, deterministic flow |
| 6 | `supervisor_agent.py` | Multi-agent | Command, Send, parallelism, agent delegation |

### Layer 2 — Production Patterns

| # | File | Pattern | New Concepts |
|---|---|---|---|
| 7 | `base_agent.py` | BaseAgent + Mixins | CostTrackingMixin, LoggingMixin, AuthMixin |
| 8 | `persist_agent.py` | SqliteSaver | Persistence between sessions, checkpoint restore |
| 9 | `hitl_agent.py` | Human in the Loop | interrupt(), approval gate, resume from checkpoint |
| 10 | `rag_agent.py` | RAG pipeline | `text-embedding-3-small` via LiteLLM, Qdrant in-memory, cross-lingual retrieval |
| 11 | `streaming_agent.py` | Token streaming | stream(), astream(), Gradio incremental output |
| 12 | `structured_agent.py` | Structured output | Pydantic models, with_structured_output(), guaranteed JSON |
| 13 | `async_agent.py` | Async + polling | job_id, ainvoke(), background task, webhook callback |

### Layer 3 — Enterprise & Deploy

| # | File | Pattern | New Concepts |
|---|---|---|---|
| 14 | `secure_agent.py` | Security | Prompt injection detection, input validation, output sanitization |
| 15 | `tenant_agent.py` | Multi-tenant | Budget isolation per user, thread_id namespacing, quota enforcement |
| 16 | `auth_agent.py` | SSO / Active Directory | Identity context, role-based access, per-call audit trail |
| 17 | `approval_agent.py` | Approval workflow | HITL for sensitive operations, manager sign-off, escalation path |
| 18 | `test_agent.py` | Testing | pytest, LLM mock, Langfuse batch evals, regression checks |
| 19 | `deploy_agent.py` | Deploy + Interop | Docker, Azure Container Apps, n8n integration, A2A protocol, cross-framework agent communication |
| 20 | `capstone_agent.py` | Production-ready | src/tools/, src/nodes/, src/graphs/, src/mixins/ — full separation of concerns, pytest |

---

## 9. Learn Mode — Working with GitHub Copilot

> **GitHub Copilot subscription required:**
> Learn Mode works with any Copilot plan:
 > - **Free** — available to all GitHub users, includes Claude Sonnet with a monthly message limit. Good enough to complete the full curriculum. See current limits: [github.com/features/copilot#pricing](https://github.com/features/copilot#pricing)
> - **Pro** ($10/month) — higher limits, recommended for extended learning sessions
> - **Business/Enterprise** — for corporate teams
>
> To activate Copilot in VS Code: install the **GitHub Copilot** extension from the Extensions marketplace → sign in with your GitHub account.

> **Important:** Before starting, make sure GitHub Copilot is set to use **Claude Sonnet 4.6** as the model.
> In VS Code: open Copilot Chat → click the model selector (top of chat panel) → select **Claude Sonnet 4.6**.
> This model is required for Learn Mode to work correctly — other models may not follow the block-by-block teaching format.

This project was built using a **block-by-block learning method** with GitHub Copilot.
If you want to learn an agent the same way, type **"Learn Mode — I want to build 01 Hello Agent"** at the start of your Copilot session (replace the number and name with the lab you want to build).

> ⚠️ **Before you start:** Always pull the latest version first:
> ```bash
> git pull
> ```
> Then make sure all dependencies are installed:
> ```bash
> uv pip install -r requirements.txt
> ```
> This ensures you have the latest agents, instructions, and framework changes before building anything new.

Copilot will then:
- Dictate one logical block at a time (docstring, imports, contract vars, one node, one tool, etc.)
- Explain every block: what it does, why it's written this way, what happens if written differently
- Wait for your confirmation before moving to the next block
- Run the agent together at the end — and always provide a **Test Checklist**: what inputs to send, what output to expect, what to verify in the trace log
- Never skip ahead — always build from simple to complex

### Block sizes
| Block | What it contains |
|---|---|
| Docstring | The whole `""" ... """` section |
| Imports | All `from ... import ...` lines together |
| Contract vars | `AGENT_NAME`, `AGENT_TYPE`, `AGENT_DESCRIPTION`, `trace_log` |
| One tool | The full `@tool` function |
| One node | The full `def node_xxx()` function |
| Graph | The full `build_graph()` function |
| Entry point | `_graph = build_graph()` + `run_agent()` |

### Example
```
You:  Learn Mode — I want to build 04 Router Agent
Copilot: [gives the full docstring block, explains it, waits for "next"]
```

**Rules during Learn Mode:**
- You type every block yourself — no copy-paste
- Ask questions at any point — no question is too simple
- We test at the end — every agent must run before moving to the next

---

## 10. Test Mode — Verifying a Finished Agent

If you have already built an agent (or copied it from `labs/`) and want to **verify it works** and **understand every concept**, use **Test Mode**.

Test Mode does not teach block by block. It is for understanding and verifying a finished agent.

> **No code writing required.** Copilot does the analysis — you just run the tests in Studio.

### How to activate

Type in the Copilot chat (replace the number and name with the lab you want):

```
Test Mode — I want to test 09 HITL Agent
```

Copilot will respond with:

1. **Setup block** — exact copy commands with full paths:
   ```
   From: labs/09-hitl-agent/solution/hitl_agent.py
   To:   src/agents/hitl_agent.py
   ```
   Plus any infrastructure steps (e.g. `docker compose up -d redis` for Lab 13)

2. **Test Checklist** — one row per test case:
   | # | Input | Expected output | Code path covered |
   |---|---|---|---|
   | 1 | `"Hello"` | Normal LLM response | `node_detect` → `node_chat` → END |
   | 2 | `"delete all files"` | Agent pauses for approval | `node_detect` → `interrupt()` |
   | ... | ... | ... | ... |

3. **Why this test** — after each row, Copilot explains which node or edge the test exercises and why it matters

4. **Concept Breakdown** — for every non-trivial construct in the agent (`ToolNode`, `interrupt()`, `SqliteSaver`, etc.):
   - What it is
   - Why it was used in this specific lab
   - What would break if you removed it
   - The one rule to remember

### Example session

```
You:      Test Mode — I want to test 09 HITL Agent
Copilot:  [reads labs/09-hitl-agent/solution/hitl_agent.py]
          [reads labs/09-hitl-agent/INSTRUCTIONS.md]
          ### Setup — HITL Agent
          1. Copy: labs/09-hitl-agent/solution/hitl_agent.py → src/agents/hitl_agent.py
          2. No extra infrastructure — SQLite creates memory.db automatically
          3. python studio.py → select HITL Agent

          ### Test Checklist — HITL Agent
          | # | Input | Expected output | Code path |
          ...

          ### Concept Breakdown — HITL Agent
          #### interrupt()
          - What it is: ...
          - Why used here: ...
          ...
```

### When to use Test Mode vs Learn Mode

| Situation | Use |
|---|---|
| You want to build an agent from scratch, step by step | **Learn Mode** |
| You already have the agent file and want to test + understand it | **Test Mode** |
| You copied a solution file and want to know what every part does | **Test Mode** |
| You finished Learn Mode and want the full test suite | Start with Learn Mode → switch to Test Mode |

---

## 11. LangGraph Core Concepts

### The Factory Analogy

| LangGraph concept | Real-world analogy |
|---|---|
| **Graph** | The factory — defines the full production process |
| **Node** | A workstation — receives input, does one job, passes output forward |
| **Edge** | The conveyor belt — moves the product from one station to the next |
| **State** | The product itself — carries all data as it moves through the factory |
| **Tool** | A machine a worker can use — called by the LLM when it decides to use it |
| **START** | The factory entrance — where every run begins |
| **END** | The factory exit — where every run finishes |

### What is a Node?

A **node** is a plain Python function that:
1. Receives the current `state`
2. Does something (LLM call, tool call, routing, transformation)
3. Returns only the fields it changed — a **partial state update**

```python
def node_extract(state: State) -> dict:
    response = llm.invoke(...)
    return {"extracted": response.content}  # only writes what it changed
```

A node does NOT have to call an LLM — it can be any Python logic: validation, API call, data transformation, logging.

### What is a Tool?

A **tool** is a function the LLM can call dynamically when it decides it needs external data or computation.

```python
@tool
def calculate(expression: str) -> str:
    """Evaluates a math expression. Use when user asks to compute something."""
    return str(eval(expression, {"__builtins__": {}}, {}))
```

The LLM reads the **docstring** to decide when to use it. The docstring is mandatory.

### Node vs Tool

| | Node | Tool |
|---|---|---|
| Who calls it? | LangGraph (graph engine) | The LLM (when it decides to) |
| When does it run? | Always, at the defined edge | Only if LLM requests it |
| How to define? | `def node_xxx(state)` | `@tool def xxx()` |
| In trace log? | `node [node_xxx]` | `tool [calculate]` |

---

## 12. Reading the Studio Trace Log

The Studio debug UI shows a **Trace Log** for every agent run. This is your primary debugging tool.

### What each entry shows

```
#01  user -> extract          node [node_extract]   [EXTRACT]
     model = gpt-5.4-nano | temp = 0.0
     What is a pipeline agent?
```

| Part | What it means |
|---|---|
| `#01` | Step number in execution order |
| `user -> extract` | Which component sent data to which |
| `node [node_extract]` | The exact Python function that created this entry |
| `[EXTRACT]` | Short label badge — the `label` field in `trace_log.append()` |
| `model = gpt-5.4-nano` | The LLM model used at this step |
| `temp = 0.0` | Temperature configured — `0.0` = deterministic, `0.7` = creative |
| Content line | First 100 chars of the input/output at this step |

### Badge colors by type

| Badge color | `type` value | Meaning |
|---|---|---|
| Cyan | `node_exec` | A LangGraph node was entered |
| Blue | `tool_call` | LLM decided to call a tool |
| Purple | `tool_result` | Tool returned a result |
| Light purple | `llm_response` | LLM produced the final response |
| Orange | `graph_call` | Agent called a sub-graph |
| Yellow | `graph_result` | Sub-graph returned a result |

### What to verify when testing an agent

| Agent type | What to check in trace |
|---|---|
| **Hello Agent** | 2 entries: `user -> llm`, `llm -> user` |
| **Chat Agent** | 2 entries per message, same node `node_chat` each time |
| **Tools Agent** | If tool used: `user->llm`, `tool_call`, `tool_result`, `llm->user` |
| **Router Agent** | `Classify` always first, then only ONE of: `Answer`, `Greet`, `Fallback` |
| **Pipeline Agent** | Always exactly 3 entries: `Extract`, `Transform`, `Respond` — in that order |

### Debug checklist for every agent run

1. **Count the steps** — matches expected? (e.g. Pipeline = always 3)
2. **Check the `node [...]` badge** — is it the function you expect?
3. **Check `model`** — is it the right model for that node?
4. **Check `temp`** — matches what you configured?
5. **Read the content** — does the data look correct at each step?

---

## 13. Docker — Useful Commands

> Docker is required for **Lab 13 (Async Agent)** and later labs that use Redis or other services.
> Install Docker Desktop from [https://www.docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop).
> After installation, restart your machine. On corporate laptops, you may need to disable **Kernel DMA Protection** in BIOS.

---

### Start / Stop Services

| Command | What it does |
|---|---|
| `docker compose up -d redis` | Start only the Redis container in background |
| `docker compose up -d` | Start all services defined in `compose.yml` |
| `docker compose stop` | Stop all containers without deleting them |
| `docker compose down` | Stop and remove all containers (data is lost) |
| `docker compose restart redis` | Restart only the Redis container |

> `-d` means **detached** — runs in background, terminal is free to use.

---

### Inspect Running Containers

| Command | What it does |
|---|---|
| `docker ps` | List all running containers (name, status, ports) |
| `docker ps -a` | List all containers including stopped ones |
| `docker stats` | Live CPU / memory usage per container |
| `docker logs redis` | Show Redis logs |
| `docker logs redis -f` | Follow Redis logs in real time (`Ctrl+C` to exit) |

---

### Redis CLI — Inspect Job Data (Lab 13)

Enter the Redis shell directly inside the running container:

```powershell
docker exec -it redis redis-cli
```

Once inside the Redis CLI:

| Command | What it does |
|---|---|
| `KEYS *` | List all stored job IDs |
| `GET job:<uuid>` | Read the stored JSON for a specific job |
| `TTL job:<uuid>` | Remaining time-to-live in seconds (returns -2 if expired) |
| `DEL job:<uuid>` | Manually delete a job entry |
| `FLUSHALL` | Delete everything in Redis — use with caution |
| `exit` | Leave the Redis CLI |

> **Example session:**
> ```
> 127.0.0.1:6379> KEYS *
> 1) "job:3f2a1b4c-..."
> 127.0.0.1:6379> GET job:3f2a1b4c-...
> "{\"status\": \"done\", \"result\": \"ainvoke is...\"}"
> 127.0.0.1:6379> TTL job:3f2a1b4c-...
> (integer) 3542
> ```

---

### Troubleshooting

| Problem | Fix |
|---|---|
| `docker: command not found` | Docker Desktop is not installed or not running — start it from the taskbar |
| `Cannot connect to the Docker daemon` | Docker Desktop is installed but not running — open it from the Start menu |
| `redis: port 6379 already in use` | Another Redis instance is running — `docker compose down` then retry |
| Container starts then immediately stops | Run `docker logs redis` to see the error |
| Can't enable virtualization | In BIOS: Security → Virtualization → Kernel DMA Protection → **Disabled** → F10 to save |

