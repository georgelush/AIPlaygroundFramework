# Agent 2 — Chat Agent

## What it demonstrates
A single-node `StateGraph` with **in-session memory** — the agent remembers everything said in the current conversation.
First agent to introduce a real LangGraph graph.

## LangGraph concepts
- `StateGraph` — the graph container
- `START` / `END` — graph entry and exit points
- `MessagesState` — built-in state that holds a list of messages
- `MemorySaver` — in-memory checkpointer that persists state between invocations
- `thread_id` — identifies a conversation session (same thread = shared memory)

---


## How to build this agent

### STEP 1  Create the agent file
Create this file and leave it completely empty:
**Path:** `src/agents/chat_agent.py`

### STEP 2  Build in Learn Mode
Type this in GitHub Copilot Chat:
```
Learn Mode  I want to build 02 Chat Agent
```
Copilot will guide you block by block through each section below.

### STEP 3  Test in Studio
```powershell
python studio.py
```
Select **Chat Agent** from the dropdown.

---

## Code structure — bloc by bloc

### Bloc 1 — Imports
```python
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import SystemMessage, HumanMessage
from src.config import LLM_MODEL, LLM_PROXY, LLM_API_KEY, langfuse_handler, get_llm_temperature
from langchain_openai import ChatOpenAI
```
─────────────────────────────────────────────────────────────────────────────
- `MessagesState` — pre-built state with a `messages: list[BaseMessage]` field
- `MemorySaver` — stores checkpoints in memory; reset on server restart
- Always import `START` and `END` — never use `"__start__"` / `"__end__"` strings

### Bloc 2 — Contract variables
```python
AGENT_NAME = "Chat Agent"
AGENT_TYPE = "chat"
trace_log: list[dict] = []
```
─────────────────────────────────────────────────────────────────────────────

### Bloc 3 — LLM + node
```python
llm = ChatOpenAI(model=LLM_MODEL, ...)

def node_chat(state: MessagesState) -> dict:
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    response = llm.invoke(messages, config={"callbacks": [langfuse_handler]})
    return {"messages": state["messages"] + [response]}
```
─────────────────────────────────────────────────────────────────────────────
- Node receives full state, returns only the fields it changed (partial update)
- `SYSTEM_PROMPT` prepended on every call — LLM always has its instructions fresh
- Return `{"messages": state["messages"] + [response]}` — never mutate state in-place

### Bloc 4 — build_graph
```python
def build_graph():
    memory = MemorySaver()
    g = StateGraph(MessagesState)
    g.add_node("chat", node_chat)
    g.add_edge(START, "chat")
    g.add_edge("chat", END)
    return g.compile(checkpointer=memory)
```
─────────────────────────────────────────────────────────────────────────────
- `MemorySaver` is passed at compile time — not at invoke time
- `g.compile(checkpointer=memory)` — enables persistence
- Always use `build_graph()` factory — never build inline

### Bloc 5 — run_agent
```python
_graph = build_graph()

def run_agent(payload: str) -> str:
    trace_log.clear()
    config = {"configurable": {"thread_id": "default"}}
    result = _graph.invoke(
        {"messages": [HumanMessage(content=payload)]},
        config=config,
    )
    return result["messages"][-1].content or ""
```
─────────────────────────────────────────────────────────────────────────────
- `thread_id: "default"` — all Studio conversations share one thread
- `_graph` compiled once at module level — reused on every call

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
| 1 | `"My name is Alex."` | Acknowledges the name | `node_exec` → `llm_response` (2 entries) |
| 2 | `"What is my name?"` (second message, same session) | Remembers "Alex" from the previous turn | `node_exec` → `llm_response` (2 entries — memory working) |
| 3 | `"What is LangGraph?"` | Explains LangGraph | `node_exec` → `llm_response` (2 entries) |

**Why test #1:** Confirms the `HumanMessage` is correctly appended to the messages list and passed to the LLM. This is the foundation — if the message list is not built correctly, no conversation is possible.

**Why test #2:** This is the critical memory test — it verifies that `MessagesState` accumulates messages across turns. Without appending the full history on every invoke, test #2 fails and the LLM says "I don't know your name."

**Why test #3:** Verifies the `SYSTEM_PROMPT` topic restriction — only LangGraph-related questions should be answered. Confirms the `SystemMessage` is prepended before the conversation history on every call.
