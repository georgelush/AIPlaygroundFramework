# Agent 5 — Pipeline Agent

## What it demonstrates
**Deterministic sequential flow** — every node always runs in fixed order.
No branching, no conditions — input goes through extract → transform → respond every single time.

Key strength: each node can use a **different model** — cheap for mechanical steps, powerful for the final response.

## LangGraph concepts
- Multiple nodes in series with `add_edge`
- Multiple state fields (`TypedDict` with 4 fields)
- Fixed execution order — no `add_conditional_edges`
- Per-node model assignment — `llm_fast` vs `llm_smart`

---


## How to build this agent

### STEP 1  Create the agent file
Create this file and leave it completely empty:
**Path:** `src/agents/pipeline_agent.py`

### STEP 2  Build in Learn Mode
Type this in GitHub Copilot Chat:
```
Learn Mode  I want to build 05 Pipeline Agent
```
Copilot will guide you block by block through each section below.

### STEP 3  Test in Studio
```powershell
python studio.py
```
Select **Pipeline Agent** from the dropdown.

---

## Code structure — bloc by bloc

### Bloc 1 — Two LLM instances
```python
llm_fast = ChatOpenAI(model="gpt-5.4-nano", temperature=0.0)   # extract + transform
llm_smart = ChatOpenAI(model="gpt-5.1",     temperature=0.7)   # respond
```
─────────────────────────────────────────────────────────────────────────────
- `llm_fast` — ultra cheap, deterministic (temp=0.0), used for mechanical steps
- `llm_smart` — powerful and creative, used only for the final user-facing response
- This is the core cost optimization strength of the pipeline pattern

### Bloc 2 — State with 4 fields
```python
class State(TypedDict):
    raw_input: str
    extracted: str
    transformed: str
    response: str
```
─────────────────────────────────────────────────────────────────────────────
- Each node writes to its own field — no field is overwritten by another node
- All fields initialized in `run_agent` before invoking the graph
- This is the "data pipeline" pattern — each node enriches the state

### Bloc 3 — node_extract
```python
def node_extract(state: State) -> dict:
    response = llm_fast.invoke(prompt, config={"callbacks": [langfuse_handler]})
    trace_log[-1]["model"] = llm_fast.model_name
    trace_log[-1]["temperature"] = get_llm_temperature(llm_fast, 0.0)
    return {"extracted": response.content}
```
─────────────────────────────────────────────────────────────────────────────
- Appends trace entry first, then updates model/temp on `trace_log[-1]` after LLM call
- Prompt: "Extract the key intent — one sentence maximum"
- Returns only `{"extracted": ...}` — partial state update

### Bloc 4 — node_transform
```python
def node_transform(state: State) -> dict:
    response = llm_fast.invoke(prompt, config={"callbacks": [langfuse_handler]})
    return {"transformed": response.content}
```
─────────────────────────────────────────────────────────────────────────────
- Take extracted intent → reformulate into a clear, well-structured question
- Still uses `llm_fast` — no need for creative power here

### Bloc 5 — node_respond
```python
def node_respond(state: State) -> dict:
    response = llm_smart.invoke(prompt, config={"callbacks": [langfuse_handler]})
    return {"response": response.content}
```
─────────────────────────────────────────────────────────────────────────────
- First and only use of `llm_smart` — the final user-facing answer
- Receives the cleaned, well-structured `state["transformed"]` as input

### Bloc 6 — build_graph (linear)
```python
def build_graph():
    g = StateGraph(State)
    g.add_node("extract", node_extract)
    g.add_node("transform", node_transform)
    g.add_node("respond", node_respond)
    g.add_edge(START, "extract")
    g.add_edge("extract", "transform")
    g.add_edge("transform", "respond")
    g.add_edge("respond", END)
    return g.compile()
```
─────────────────────────────────────────────────────────────────────────────
- Pure linear chain — no `add_conditional_edges` anywhere
- Nodes always run in this exact order: extract → transform → respond

---

## Difference from Agent 4 (Router)
| | Router Agent | Pipeline Agent |
|---|---|---|
| Which nodes run | Only ONE (branching decides) | ALL THREE (always) |
| Branching | Yes — `add_conditional_edges` | No — all `add_edge` |
| LLM instances | One | Two (fast + smart) |
| Output field | `response` | `response` |

---

## Trace log (always 3 steps)
| Step | Type | Node | Model |
|---|---|---|---|
| 1 | `node_exec` | extract | gpt-5.4-nano |
| 2 | `node_exec` | transform | gpt-5.4-nano |
| 3 | `llm_response` | respond | gpt-5.1 |

---

## How to test in Studio

1. Run Studio: `python studio/studio.py`
2. Open **http://127.0.0.1:8000** in your browser
3. Select **Pipeline Agent** from the dropdown
4. Type your message in the **Message** field and press **Send**
5. The **Trace** panel shows each pipeline node executing in order: extract → transform → respond

## Test Checklist

| # | Input | Expected output | Trace expected |
|---|---|---|---|
| 1 | `"Summarize this: The fox jumped over the dog."` | Short summary or analysis | `node_exec` (extract, model=gpt-5.4-nano) → `node_exec` (transform, model=gpt-5.4-nano) → `llm_response` (respond, model=gpt-5.1) |
| 2 | `"Who are you?"` | Explains it is Pipeline Agent | `node_exec` → `node_exec` → `llm_response` — all 3 nodes run even for a trivial question |
| 3 | `"What does each node do?"` | Explains extract / transform / respond steps | `node_exec` → `node_exec` → `llm_response` — verify 3 entries with different model badges |

**Why test #1:** The core pipeline test — confirms all 3 nodes run in sequence and that trace entries expose the model used per node. Without this, you cannot verify the cost-optimization split (`llm_fast` for extraction, `llm_smart` for the final response).

**Why test #2:** Verifies there is no short-circuit — even a simple identity question goes through all 3 nodes. This distinguishes the pipeline pattern from a router: the pipeline never skips steps.

**Why test #3:** Confirms state flows correctly across nodes — `node_extract` writes `state["extracted"]`, `node_transform` reads it and writes `state["transformed"]`, `node_respond` reads `state["transformed"]`. If any field name is mistyped, this test produces an incoherent answer.
