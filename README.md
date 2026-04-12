# Agentic AI Playground 🚀

A production-grade AI agent framework built on **LangGraph**, **LangChain**, and **LiteLLM** — with a visual debug UI, REST API server, and a structured 20-lab learning curriculum.

Platforms: Windows 10/11 • Ubuntu 20.04+ • macOS 11+

---

## What's Inside

| Component | Description |
|---|---|
| `studio.py` | Local debug UI (Gradio) — visual trace log, live agent testing |
| `server.py` | FastAPI REST server — production / n8n integration |
| `src/agents/` | Auto-discovered agents — drop a file here, it appears in Studio |
| `src/config.py` | Shared config — LLM client, Langfuse handler, env vars |
| `src/registry.py` | Auto-discovery engine — shared by Studio and server |
| `labs/` | 20-lab structured curriculum — from Hello Agent to Capstone |

---

## Quick Start

```bash
# 1. Clone (use your GitHub Personal Access Token in the URL)
git clone https://<YOUR_TOKEN>@github.com/<ORG>/<REPO_NAME>.git
cd <REPO_NAME>

# 2. Setup — one command does everything (venv, packages, .env)
.\setup.ps1        # Windows PowerShell
./setup.sh         # Linux / macOS (run: chmod +x setup.sh first)

# 3. Run
python studio.py
# Open http://localhost:8000
```

> First time? Read [`labs/GETTING_STARTED.md`](labs/GETTING_STARTED.md) — it covers token setup, Git install, and credentials step by step.

---

## Project Structure

```
Agentic-AI-Playground/
├── src/
│   ├── agents/          # Active agents — auto-loaded by registry
│   ├── data/            # Documents indexed by RAG agent (.txt, .pdf)
│   ├── graphs/          # StateGraph definitions (shared graphs)
│   ├── nodes/           # Reusable node functions
│   ├── tools/           # Reusable @tool functions
│   ├── mixins/          # Reusable mixins (CostTrackingMixin, LoggingMixin, AuthMixin)
│   ├── config.py        # LLM client, Langfuse handler, env vars
│   └── registry.py      # Agent auto-discovery
├── labs/                # 20-lab curriculum (01–20 ✅)
│   ├── README.md
│   ├── GETTING_STARTED.md
│   └── 01–20/           # each lab: INSTRUCTIONS.md + solution/xx_agent.py
├── tests/
├── studio.py            # Gradio debug UI (port 8000)
├── server.py            # FastAPI REST server (port 8080)
├── compose.yml          # Docker services (Redis, PostgreSQL)
├── .env.example
└── requirements.txt
```

---

## Adding Your First Agent

Create a file in `src/agents/` — it appears in Studio automatically on next restart:

```python
# src/agents/my_agent.py
AGENT_NAME = "My Agent"
AGENT_TYPE = "chat"
AGENT_DESCRIPTION = "Does something useful."

trace_log: list[dict] = []

def run_agent(payload: str) -> str:
    trace_log.clear()
    return "Hello from my agent!"
```

---

## Learn Mode (GitHub Copilot)

Build agents block by block with guided explanations. In the Copilot chat:

```
Learn Mode — I want to build 01 Hello Agent
```

Copilot gives one code block at a time, explains it, and waits for **"next"** before continuing.
Full curriculum: [`labs/README.md`](labs/README.md)

## Test Mode (GitHub Copilot)

Already built an agent? Verify it without writing code. In the Copilot chat:

```
Test Mode — I want to test 01 Hello Agent
```

Copilot reads the solution file, gives a full **Test Checklist** with explanations for every test case, and breaks down every concept in the agent — what it is, why it was used, and what breaks without it. No code writing required.

---

## REST API

```bash
# Start the server
python server.py

# List agents
GET http://localhost:8080/agents

# Run an agent
POST http://localhost:8080/run
{
  "agent": "Ping Agent",
  "payload": "hello"
}
```

---

## Tech Stack

| Library / Tool | Version | Role | First used |
|---|---|---|---|
| LangGraph | 1.1.3+ | Agent graphs, StateGraph, ToolNode | Lab 02 |
| LangChain | 0.3.0+ | ChatOpenAI, bind_tools, message types | Lab 01 |
| FastAPI + uvicorn | 0.115.0+ | REST API server | framework |
| Gradio | 6.0+ | Studio debug UI | framework |
| Langfuse | 4.0.0+ | LLM observability and tracing | framework |
| LiteLLM proxy | — | LLM gateway (model: gpt-5.4-nano) | framework |
| SQLite + SqliteSaver | — | Persistent graph checkpoints between sessions | Lab 08 |
| Pydantic | 2.x | Structured output schema validation | Lab 12 |
| Qdrant | 1.9.0+ | In-memory vector store for RAG pipeline | Lab 10 |
| fastembed | 0.4.0+ | Local embedding model — no OpenAI key needed for RAG | Lab 10 |
| Redis | 5.0+ | Async job store (TTL) + HITL graph checkpointer | Lab 13 |
| langgraph-checkpoint-redis | — | Redis-backed LangGraph state persistence | Lab 20 |
| Docker Desktop | — | Container runtime for Redis | Lab 13 |
| asyncio | stdlib | Async coroutines, event loop, `ainvoke()` | Lab 13 |

---

## Documentation

| Document | Description |
|---|---|
| [`labs/GETTING_STARTED.md`](labs/GETTING_STARTED.md) | Full setup, git workflow, framework walkthrough |
| [`labs/README.md`](labs/README.md) | 20-lab curriculum, Learn Mode guide, dev standards |
| [`labs/0X-*/INSTRUCTIONS.md`](labs/) | Per-agent lab guide — blocs, trace anatomy, test checklist |

---

## Security

- Never commit `.env` — it is in `.gitignore`
- API keys go in `.env` only — never hardcoded in agents
- All LLM calls routed through the internal LiteLLM proxy — no external key exposure
- Input validation at system boundaries only (`run_agent` entry point, FastAPI endpoints)
