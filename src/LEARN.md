# LangGraph Learning Framework
> Rules, curriculum, and design decisions for building agents in this project.
> This file is the single source of truth for the learning journey.

---

## 1. How We Work Together

- **You write, I dictate** — line by line, you type each line yourself
- **I explain every line** — what it does, why it's written this way, what would happen if written differently
- **We run at the end** — every agent is tested after it's built
- **No skipping** — we build from simple to complex, never jump ahead
- After you learn, you teach the team using these same agents as examples

---

## 2. Module 0 — Git Essentials (Before Everything Else)

Git is required before touching any agent code. Every team member must know these commands.

### Daily Commands

| Command | When to use |
|---|---|
| `git clone <url>` | First time — downloads the repository to your machine |
| `git status` | See which files changed since last commit |
| `git pull` | Get the latest changes from the server before you start working |
| `git add .` | Stage all modified files for commit |
| `git commit -m "short description"` | Save a snapshot with a meaningful message |
| `git push` | Send your commits to GitHub / Azure DevOps |

### Branch Workflow (one branch per agent)

```bash
git checkout -b agent-2-chat        # create a new branch for your work
# ... write code ...
git add .
git commit -m "add agent_chat.py with MemorySaver"
git push
# open Pull Request → get review → merge to main
```

**Rule:** Never commit directly to `main`. Always use a branch.

### Commit Message Convention

```
add agent_chat.py with MemorySaver
fix None guard in run_agent
update LEARN.md curriculum to 19 agents
remove debug print from agent_tools.py
```

Short, imperative, English. No "I did...", no "Fixed the thing".

### .gitignore — What Never Gets Committed

Create this file at the root of the project:

```
.env
.venv/
__pycache__/
*.pyc
*.db
.gradio/
```

- `.env` — contains API keys and secrets — **never commit this**
- `.venv/` — Python virtual environment — each developer installs their own
- `__pycache__/` — compiled Python bytecode — auto-generated, not needed in repo
- `*.db` — SQLite databases — local data, not shared

### Common Mistakes to Avoid

| Mistake | What happens | Fix |
|---|---|---|
| Commit `.env` | API keys exposed publicly | Add `.env` to `.gitignore` immediately |
| Work directly on `main` | Breaks everyone's work | Always create a branch |
| Vague commit message `"fix"` | Nobody knows what changed | Write what exactly changed |
| `git push --force` | Overwrites others' work | Never use unless you know exactly why |

---

## 3. Curriculum — Agents We Build

Each agent demonstrates **exactly one new concept**. No business logic — pure learning.

### Layer 1 — Fundamentals

| # | File | Pattern | New Concepts |
|---|---|---|---|
| 1 | `agent_hello.py` ✅ | Simple LLM, no graph | Agent contract, trace_log, run_agent |
| 2 | `agent_chat.py` | Single-node StateGraph | StateGraph, START, END, MessagesState, MemorySaver, thread_id |
| 3 | `agent_tools.py` | ReAct loop | @tool, ToolNode, tools_condition, tool calling cycle |
| 4 | `agent_router.py` | Branching | add_conditional_edges, routing functions |
| 5 | `agent_pipeline.py` | Nodes in series | Multiple nodes, extra state fields, deterministic flow |
| 6 | `agent_supervisor.py` | Multi-agent | Command, Send, parallelism, agent delegation |

### Layer 2 — Production Patterns

| # | File | Pattern | New Concepts |
|---|---|---|---|
| 7 | `agent_base.py` | BaseAgent + Mixins | CostTrackingMixin, LoggingMixin, AuthMixin — reusable enterprise behaviors |
| 8 | `agent_persist.py` | SqliteSaver | Persistence between sessions, checkpoint restore |
| 9 | `agent_hitl.py` | Human in the Loop | interrupt(), approval gate, resume from checkpoint |
| 10 | `agent_rag.py` | RAG pipeline | Embed, vector search, augment prompt, retrieval-grounded answers |
| 11 | `agent_streaming.py` | Token streaming | stream(), astream(), Gradio incremental output |
| 12 | `agent_structured.py` | Structured output | Pydantic models, with_structured_output(), guaranteed JSON |
| 13 | `agent_async.py` | Async + polling | job_id, ainvoke(), background task, webhook callback |

### Layer 3 — Enterprise & Deploy

| # | File | Pattern | New Concepts |
|---|---|---|---|
| 14 | `agent_secure.py` | Security | Prompt injection detection, input validation, output sanitization |
| 15 | `agent_tenant.py` | Multi-tenant | Budget isolation per user, thread_id namespacing, quota enforcement |
| 16 | `agent_auth.py` | SSO / Active Directory | Identity context, role-based access, per-call audit trail |
| 17 | `agent_approval.py` | Approval workflow | HITL for sensitive operations, manager sign-off, escalation path |
| 18 | `agent_test.py` | Testing | pytest, LLM mock, Langfuse batch evals, regression checks |
| 19 | `agent_deploy.py` | Deploy | Docker, Azure Container Apps, n8n integration, on-prem config |

---

## 3. Agent Contract — Quick Reference

Every file in `src/agents/` must have these four things to be auto-registered:

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

If any of these are missing, the agent will not appear in `studio.py` or `server.py`.

---

## 4. src/ Folder — What Goes Where

```
src/
├── tools/      # Functions the LLM can call dynamically (@tool decorator)
│               # Example: get_menu(), search_web(), book_table()
│
├── nodes/      # Single steps in a graph (receive state, return partial state)
│               # Example: node_classify(), node_summarize(), node_respond()
│
├── graphs/     # StateGraph definitions — nodes connected with edges
│               # Example: chat_graph.py, research_graph.py
│
└── agents/     # Orchestrators — combines LLM + tools + graph + trace_log
                # One file per agent, each exposes run_agent()
```

Analogy: `tools` = hands, `nodes` = steps, `graphs` = recipe, `agents` = the chef.

---

## 5. LangGraph Standard — Non-Negotiable

### Imports — always use these
```python
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
```

### State — always TypedDict
```python
from langgraph.graph import MessagesState  # preferred for chat agents

# Only define manually when you need extra fields beyond messages:
from typing import TypedDict
class State(TypedDict):
    messages: list
    category: str  # extra field example
```

### ReAct Tool Loop — standard pattern
```python
tool_node = ToolNode(TOOLS)

def node_llm(state: State) -> dict:
    response = llm_with_tools.invoke(state["messages"], config={"callbacks": [langfuse_handler]})
    return {"messages": state["messages"] + [response]}

def build_graph():
    g = StateGraph(State)
    g.add_node("llm", node_llm)
    g.add_node("tools", tool_node)
    g.add_edge(START, "llm")
    g.add_conditional_edges("llm", tools_condition)  # auto-routes to "tools" or END
    g.add_edge("tools", "llm")                       # loop back after tool result
    return g.compile()
```

### Graph Invocation — always this way
```python
result = graph.invoke({"messages": [HumanMessage(content=user_input)]})
final_answer = result["messages"][-1].content  # always extract .content
```

---

## 6. Memory Design Decisions

| Type | Used? | Why |
|---|---|---|
| In-thread (RAM) | YES | Messages stay in state["messages"] during the session |
| MemorySaver (RAM checkpointer) | YES from Agent 2 | Keeps context across multiple invoke calls in one session |
| SqliteSaver (disk) | NO | Data cleared on session close — by design |
| Vector store (long-term) | NO | Not needed for learning agents |

**Rule:** When `studio.py` is closed, all conversation history is gone. This is intentional.
Each new session starts fresh.

**Implementation:** `graph.compile(checkpointer=MemorySaver())` + unique `thread_id` per session.

---

## 7. Design Principles

Every agent in this framework follows these principles:

### Self-aware
Each agent knows who it is and can explain itself. The `SYSTEM_PROMPT` always includes:
- What the agent is
- Why it was created
- What concept it demonstrates
- What the user can do with it

```python
SYSTEM_PROMPT = """
You are Agent Hello — the first agent in the LangGraph learning series.
Your purpose: demonstrate the basic agent contract (no graph).
Concepts you teach: AGENT_NAME, AGENT_TYPE, trace_log, run_agent.
If asked who you are or why you exist — explain exactly this.
"""
```

### Single responsibility
Each agent teaches exactly one new concept. No mixing concerns.

### In-session memory only
Agents remember the conversation within a session. On close — clean slate.

### Always explainable
Every line of code has a reason. No magic, no shortcuts that hide how things work.

---

## 8. Language Rules — Always Enforce

- **All code comments** → English only, never Romanian or any other language
- **All `AGENT_NAME` values** → English, Title Case (e.g. `"Hello Agent"`, `"Research Agent"`)
- **All variable names, function names, node names** → English only
- **All tool docstrings** → English only (the LLM reads these to decide when to call the tool)
- **All strings visible to LLM** (system prompts, tool descriptions) → English only

These rules apply to every file in the project, without exception.

---

## 9. Labs for the Team (TODO — filled after you complete the curriculum)

After finishing all 19 agents, each becomes a lab exercise:

### Layer 1 Labs — Fundamentals

| Lab | Agent to study | Exercise |
|---|---|---|
| Lab 1 | `agent_hello.py` | Add a second trace_log entry; change SYSTEM_PROMPT, observe output |
| Lab 2 | `agent_chat.py` | Change thread_id mid-session — observe memory reset |
| Lab 3 | `agent_tools.py` | Add a new @tool function with a mandatory docstring |
| Lab 4 | `agent_router.py` | Add a third route branch to an existing conditional edge |
| Lab 5 | `agent_pipeline.py` | Insert a new node between two existing nodes |
| Lab 6 | `agent_supervisor.py` | Add a fourth sub-agent using Command and Send |

### Layer 2 Labs — Production Patterns

| Lab | Agent to study | Exercise |
|---|---|---|
| Lab 7 | `agent_base.py` | Add a new mixin method; apply it to an existing agent |
| Lab 8 | `agent_persist.py` | Resume a conversation from a previous session using checkpoint ID |
| Lab 9 | `agent_hitl.py` | Implement a two-step approval (request + confirm) |
| Lab 10 | `agent_rag.py` | Swap the vector store backend; observe retrieval differences |
| Lab 11 | `agent_streaming.py` | Add streaming to an existing non-streaming agent |
| Lab 12 | `agent_structured.py` | Add a new required field to the Pydantic output model |
| Lab 13 | `agent_async.py` | Add a webhook callback to an existing async agent |

### Layer 3 Labs — Enterprise & Deploy

| Lab | Agent to study | Exercise |
|---|---|---|
| Lab 14 | `agent_secure.py` | Add a new injection pattern to the detection list |
| Lab 15 | `agent_tenant.py` | Add per-tenant rate limiting on top of budget isolation |
| Lab 16 | `agent_auth.py` | Add a new role with restricted tool access |
| Lab 17 | `agent_approval.py` | Add a timeout — auto-reject if no approval within 60s |
| Lab 18 | `agent_test.py` | Write a new pytest case that mocks LLM output |
| Lab 19 | `agent_deploy.py` | Add an environment variable for on-prem vs cloud routing |

> This section will be expanded with full lab instructions after the curriculum is complete.
