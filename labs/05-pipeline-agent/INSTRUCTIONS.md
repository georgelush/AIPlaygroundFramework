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

## Test checklist
| Input | Expected output | What to watch in trace |
|---|---|---|
| `"Summarize this: The fox jumped over the dog."` | Summary/analysis | Step 1 model=gpt-5.4-nano, Step 3 model=gpt-5.1 |
| `"Who are you?"` | Explains Pipeline Agent | All 3 steps always run even for simple questions |
| `"What does each node do?"` | Explains extract/transform/respond | Verify 3 trace entries, different models |
