# Agentic AI Playground — Lab Guide

A structured, hands-on curriculum teaching developers how to build AI agents with the **Agentic AI Playground** framework — a production-grade agent framework built on LangGraph, LangChain, and LiteLLM.

---

## Overview

This curriculum is designed for mixed-experience teams: developers who know Python but not LLMs, and developers who know LLMs but not LangGraph. Labs are self-contained and build on each other progressively — completing them in order is strongly recommended.

**Module 1 — LangGraph Agent Foundations (Labs 01–06)** ✅ complete.

**Module 2 — Production Patterns (Labs 07–13)** ✅ complete.

**Module 3 — Enterprise & Deploy (Labs 14–20)** ✅ complete.

Each lab introduces one new LangGraph pattern. By Lab 06, you will have built a fully working multi-agent supervisor system from scratch.

---

## Prerequisites

Before starting any lab you need:

- Python 3.12+
- Git
- Access to the LiteLLM proxy (see `.env.example` at project root)
- VS Code with GitHub Copilot (recommended — enables Learn Mode)

No prior LangGraph knowledge required. The framework setup is covered in Lab 01.

---

## Labs

### Module 1 — LangGraph Agent Foundations ✅

| # | Title | Pattern introduced | Time |
|---|---|---|---|
| 01 | Hello Agent | Direct LLM call, agent contract, trace_log | 20–30 min |
| 02 | Chat Agent | StateGraph, MessagesState, MemorySaver, thread_id | 30–40 min |
| 03 | Tools Agent | @tool, bind_tools, ToolNode, tools_condition, ReAct loop | 40–55 min |
| 04 | Router Agent | TypedDict State, add_conditional_edges, routing functions | 40–55 min |
| 05 | Pipeline Agent | Sequential nodes, multiple state fields, per-node model assignment | 40–55 min |
| 06 | Supervisor Agent | Multi-agent coordination, AGENT_MAP, agent-to-agent calls | 50–70 min |

### Module 2 — Production Patterns ✅

| # | Title | Pattern introduced | Time |
|---|---|---|---|
| 07 | Base Agent | BaseAgent + Mixins — CostTrackingMixin, LoggingMixin, AuthMixin | 40–55 min |
| 08 | Persist Agent | SqliteSaver — persistence between sessions, checkpoint restore | 30–45 min |
| 09 | HITL Agent | Human in the Loop — interrupt(), Command(resume=), approval gate | 50–70 min |
| 10 | RAG Agent | RAG pipeline — text-embedding-3-small, Qdrant in-memory, cross-lingual retrieval | 60–80 min |
| 11 | Streaming Agent | Token streaming — llm.stream(), Generator, yield, Gradio incremental output | 30–45 min |
| 12 | Structured Agent | Structured output — Pydantic models, with_structured_output(), guaranteed JSON | 30–45 min |
| 13 | Async Agent | Async + polling — `job_id`, `ainvoke()`, background task, Redis TTL, webhook callback | 60–80 min ⚠️ Docker |

> ⚠️ Lab 13 requires Docker: run `docker compose up -d redis` before starting Studio.

### Module 3 — Enterprise & Deploy ✅

| # | Title | Pattern introduced | Time |
|---|---|---|---|
| 14 | Secure Agent | Security gate — prompt injection detection, input sanitization, output validation | 40–55 min |
| 15 | Tenant Agent | Multi-tenant — budget isolation per user, `thread_id` namespacing, quota enforcement | 40–55 min |
| 16 | Auth Agent | RBAC — identity context, role-based access, per-call audit trail, `@user` Studio format | 40–55 min |
| 17 | Approval Agent | Approval workflow — HITL gate for sensitive ops, in-memory pending queue, manager sign-off | 50–70 min |
| 18 | Test Agent | Automated testing — `pkgutil` auto-discovery, `MagicMock`, `patch`, contract and trace assertions | 60–80 min |
| 19 | Deploy Agent | REST deploy — server status introspection, health check, VS Code port forwarding, n8n HTTP Request | 60–80 min |
| 20 | Capstone Agent | Capstone — multi-file architecture, RAG + Redis HITL checkpointer + dual-LLM + multi-tenant budget | 80–100 min ⚠️ Docker |

> ⚠️ Lab 20 requires Docker: run `docker compose up -d redis` before starting Studio.

---

## Repository Structure

```
labs/
├── README.md                          ← you are here
├── GETTING_STARTED.md                 ← setup, first run, framework overview
│
├── 01-hello-agent/                    ✅
│   ├── INSTRUCTIONS.md
│   └── solution/
│       └── hello_agent.py
├── 02-chat-agent/                     ✅
│   ├── INSTRUCTIONS.md
│   └── solution/
│       └── chat_agent.py
├── 03-tools-agent/                    ✅
│   ├── INSTRUCTIONS.md
│   └── solution/
│       └── tools_agent.py
├── 04-router-agent/                   ✅
│   ├── INSTRUCTIONS.md
│   └── solution/
│       └── router_agent.py
├── 05-pipeline-agent/                 ✅
│   ├── INSTRUCTIONS.md
│   └── solution/
│       └── pipeline_agent.py
├── 06-supervisor-agent/               ✅
│   ├── INSTRUCTIONS.md
│   └── solution/
│       └── supervisor_agent.py
├── 07-base-agent/                     ✅
│   ├── INSTRUCTIONS.md
│   └── solution/
│       └── base_agent.py
├── 08-persist-agent/                  ✅
│   ├── INSTRUCTIONS.md
│   └── solution/
│       └── persist_agent.py
├── 09-hitl-agent/                     ✅
│   ├── INSTRUCTIONS.md
│   └── solution/
│       └── hitl_agent.py
│
├── 10-rag-agent/                      ✅
│   ├── INSTRUCTIONS.md
│   └── solution/
│       ├── rag_agent.py
│       └── data/
│           └── langgraph_concepts.txt
├── 11-streaming-agent/                ✅
│   ├── INSTRUCTIONS.md
│   └── solution/
│       └── streaming_agent.py
├── 12-structured-agent/               ✅
│   ├── INSTRUCTIONS.md
│   └── solution/
│       └── structured_agent.py
├── 13-async-agent/                    ✅
│   ├── INSTRUCTIONS.md
│   └── solution/
│       └── async_agent.py
│
├── 14-secure-agent/                   ✅
│   ├── INSTRUCTIONS.md
│   └── solution/
│       └── secure_agent.py
├── 15-tenant-agent/                   ✅
│   ├── INSTRUCTIONS.md
│   └── solution/
│       └── tenant_agent.py
├── 16-auth-agent/                     ✅
│   ├── INSTRUCTIONS.md
│   └── solution/
│       └── auth_agent.py
├── 17-approval-agent/                ✅
│   ├── INSTRUCTIONS.md
│   └── solution/
│       └── approval_agent.py
├── 18-test-agent/                     ✅
│   ├── INSTRUCTIONS.md
│   └── solution/
│       └── test_agent.py
├── 19-deploy-agent/                   ✅
│   ├── INSTRUCTIONS.md
│   └── solution/
│       └── deploy_agent.py
└── 20-capstone-agent/                 ✅  ⚠️ docker compose up -d redis
    ├── INSTRUCTIONS.md
    └── solution/
        ├── capstone_agent.py
        ├── tools/
        │   └── hr_tools.py
        ├── nodes/
        │   └── hr_nodes.py
        └── graphs/
            └── hr_graph.py
```

Each lab folder contains:
- `INSTRUCTIONS.md` — step-by-step instructions, bloc-by-bloc code, trace log anatomy, test checklist
- `solution/` — complete, runnable reference implementation

---

## Quick Start

```bash
# 1. Clone the repo
git clone <repo-url>
cd "Agentic-AI-Playground"

# 2. Create virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # Linux/macOS

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Fill in: LLM_PROXY, LLM_API_KEY, LLM_MODEL, LANGFUSE_*

# 5. Start Studio
python studio.py
# Open http://localhost:8000
```

Start with Lab 01:
```
open labs/01-hello-agent/INSTRUCTIONS.md
```

---

## How Learn Mode Works (GitHub Copilot)

Each lab is designed to be built **bloc by bloc** with GitHub Copilot in **Learn Mode**.

To activate Learn Mode, type in the Copilot chat:

```
Learn Mode — I want to build 01 Hello Agent
```

Copilot will:
1. Give you **one code bloc at a time**
2. Explain what each bloc does and why
3. Wait for you to write it and say **"next"** before continuing
4. At the end, provide a **Test Checklist** to verify in Studio

This mode is enforced in `.github/copilot-instructions.md` — it activates automatically when you use the phrase above.

## How Test Mode Works (GitHub Copilot)

If you have already built an agent and want to **understand it or verify it works**, use **Test Mode** instead of Learn Mode.

To activate Test Mode, type in the Copilot chat:

```
Test Mode — I want to test 09 HITL Agent
```

(Replace the number and name with the lab you want to test.)

Copilot will:
1. Read the actual solution file for that lab — no hallucinated tests
2. Give you a **Setup block** with exact file paths to copy (e.g. `labs/09-hitl-agent/solution/hitl_agent.py` → `src/agents/hitl_agent.py`)
3. Output a full **Test Checklist** — one row per test case, covering every code path
4. Explain **why each test exists** — which node, edge, or condition it verifies
5. Break down every concept used in the agent: what it is, why it was chosen, what breaks without it

**Test Mode does not ask you to write code.** It is purely for understanding and verification.

This mode is enforced in `.github/copilot-instructions.md` — it activates automatically when you use the phrase above.

---

## Key Concepts by Lab

| Concept | Introduced in |
|---|---|
| `AGENT_NAME`, `AGENT_TYPE`, `trace_log`, `run_agent` | Lab 01 |
| `StateGraph`, `START`, `END`, `MessagesState`, `MemorySaver`, `thread_id` (in-session memory) | Lab 02 |
| `@tool`, `bind_tools`, `ToolNode`, `tools_condition`, ReAct loop (llm → tools → llm) | Lab 03 |
| `TypedDict` State, `add_conditional_edges`, routing functions, multiple terminal nodes | Lab 04 |
| Sequential pipeline, per-node model assignment, `llm_fast` vs `llm_smart` cost optimization | Lab 05 |
| Multi-agent coordination, `AGENT_MAP`, `graph_call` / `graph_result` trace types | Lab 06 |
| `CostTrackingMixin`, `LoggingMixin`, `AuthMixin`, BaseAgent pattern | Lab 07 |
| `SqliteSaver`, `thread_id` (persistent memory), checkpoint restore | Lab 08 |
| `interrupt()`, `Command(resume=)`, approval gate, HITL with persistence | Lab 09 |
| `text-embedding-3-small`, Qdrant in-memory vector store, RAG pipeline, cross-lingual retrieval | Lab 10 |
| `llm.stream()`, `Generator`, `yield`, Gradio incremental output | Lab 11 |
| `Pydantic` models, `with_structured_output()`, guaranteed JSON schema | Lab 12 |
| `ainvoke()`, `asyncio.run()`, `threading.Thread`, `job_id` polling, Redis TTL, webhook callback | Lab 13 |
| Gate node pattern, `security_error`, prompt injection detection, input validation, output sanitization | Lab 14 |
| Budget isolation, `quota_error`, `thread_id` namespacing, in-memory tenant storage, context injection | Lab 15 |
| RBAC, `auth_error`, `ROLE_PERMISSIONS`, `audit_log`, `_detect_action`, `@user message` Studio format | Lab 16 |
| `interrupt()`, `Command(resume=)`, manager approval gate, escalation path, sensitive operation detection | Lab 17 |
| `pkgutil` agent auto-discovery, `MagicMock`, `patch`, contract validation, trace assertions | Lab 18 |
| FastAPI REST server, LangGraph Platform standard, port tunneling via VS Code Dev Tunnels, n8n integration | Lab 19 |
| Multi-file architecture (`src/tools/`, `src/nodes/`, `src/graphs/`), Redis HITL checkpointer, dual-LLM classifier, multi-tenant token budget, self-approval gate | Lab 20 |

---

## Studio Trace Log

Every agent produces a visual execution trace in Studio. Trace entry badge colors:

| Color | Type | Meaning |
|---|---|---|
| Cyan | `node_exec` | A LangGraph node was entered |
| Blue | `tool_call` | LLM decided to call a tool |
| Purple | `tool_result` | Tool returned a result |
| Light purple | `llm_response` | LLM produced a final response |
| **Orange** | `graph_call` | Agent called a sub-agent |
| **Yellow** | `graph_result` | Sub-agent returned a result |

Each entry shows: `from → to`, badge type, model name, temperature, and content preview.

---

## Development Standards

### Think Before Coding
- State assumptions explicitly before implementing
- Surface multiple interpretations — never pick silently
- Suggest simpler approaches when warranted

### Simplicity First
- Minimum code that solves the problem
- No features beyond what was requested
- No abstractions for single-use code

### Surgical Changes
- Touch only what the task requires
- Match existing style
- Every changed line traces to the stated purpose

### Language Rules
- All code, comments, docstrings, variable names: **English only**
- All `AGENT_NAME` values: Title Case English, no diacritics
- Tool docstrings: English only — the LLM reads them

### Agent Contract (non-negotiable)
Every file in `src/agents/` must define:
```python
AGENT_NAME = "..."          # Title Case English string
AGENT_TYPE = "chat"         # "chat" | "processor" | "pipeline"
AGENT_DESCRIPTION = "..."   # shown in GET /agents
trace_log: list[dict] = []  # never reassign — always .clear()

def run_agent(payload: str) -> str:
    trace_log.clear()
    ...
    return result or ""
```

### Trace Log Contract
Every trace entry must include:
```python
trace_log.append({
    "type":        "node_exec",   # see types table above
    "label":       "Classify",    # short badge text
    "from":        "user",
    "to":          "llm",
    "arrow":       "->",
    "content":     payload[:200],
    "fn":          "node_classify",  # Python function name
    # optional:
    "model":       llm.model_name,
    "temperature": get_llm_temperature(llm, 0.3),
})
```

### LangGraph Rules
- Always import `START` and `END` — never use `"__start__"` / `"__end__"` strings
- Use `ToolNode` and `tools_condition` from `langgraph.prebuilt` — never implement manually
- Node functions return **partial state** only — never mutate state in-place
- Call `g.compile()` once at module level — reuse on every invocation
- Always use `build_graph()` factory function — never build inline

### Naming Conventions
| Thing | Convention | Example |
|---|---|---|
| Agent file | `<name>_agent.py` | `hello_agent.py` |
| Node function | `node_` prefix | `node_classify()` |
| Graph builder | always `build_graph()` | — |
| Tool function | verb + noun | `get_menu()`, `calculate_total()` |
| State class | always `State` | `class State(TypedDict)` |
