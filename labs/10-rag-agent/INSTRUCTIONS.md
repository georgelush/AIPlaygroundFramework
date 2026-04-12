# Agent 10 — RAG Agent

## What it demonstrates
**Retrieval-Augmented Generation (RAG)** — instead of answering from the LLM's training memory,
the agent loads documents from `src/data/`, indexes them in a Qdrant in-memory vector store,
retrieves the most relevant chunks for each query, and passes them as context to the LLM.

## New concepts vs Agent 9 (HITL Agent)
| | HITL Agent (Lab 09) | RAG Agent (Lab 10) |
|---|---|---|
| Pattern | interrupt() approval gate | Embed → search → augment → generate |
| LLM input | User message only | User message + retrieved context |
| External data | None | Documents from `src/data/*.txt` |
| Vector store | None | Qdrant in-memory |
| Embedding model | None | `text-embedding-3-small` via LiteLLM proxy |
| Graph nodes | detect → chat | retrieve → generate |

## LangGraph concepts
- `TypedDict State` with custom fields — `query`, `context`, `answer` instead of `messages`
- Two-node sequential graph — `retrieve` always runs before `generate`
- Partial state update — each node writes only the field it produces
- No tools, no branching, no loop — the simplest multi-node deterministic pipeline

## RAG concepts
- **Document loading** — `DirectoryLoader` reads all `.txt` files from `src/data/`
- **Chunking** — `RecursiveCharacterTextSplitter` splits documents into 500-char chunks with 50-char overlap
- **Embedding** — `OpenAIEmbeddings` via LiteLLM proxy converts each chunk into a 1536-dimension vector (multilingual, 100+ languages)
- **Vector store** — `QdrantVectorStore` stores vectors in memory using cosine similarity
- **Semantic search** — `similarity_search(query, k=3)` retrieves the 3 most relevant chunks
- **Context augmentation** — the LLM receives `Context: [...chunks...]\n\nQuestion: [query]`

## Embedding model — fastembed vs text-embedding-3-small

### Full comparison

| | `fastembed` (BAAI/bge-small-en-v1.5) | `text-embedding-3-small` (OpenAI) |
|---|---|---|
| Where it runs | Local — in your RAM | Cloud — via LiteLLM proxy |
| API key | No — zero configuration | Yes — same key as LLM |
| Cost | Free | ~$0.02 / million tokens |
| Languages | **English only** | **100+ languages** |
| Vector dimensions | 384 | 1536 |
| Retrieval quality | Good for English | Better — richer semantic space |
| First run | Downloads ~130 MB once | Instant |
| Works offline | Yes | No — needs proxy |
| Code line | `FastEmbedEmbeddings(model_name="BAAI/bge-small-en-v1.5")` | `OpenAIEmbeddings(model="text-embedding-3-small", base_url=LLM_PROXY, api_key=LLM_API_KEY)` |
| `EMBEDDING_DIM` | `384` | `1536` |

---

### The key difference — language

The biggest practical difference is how they handle **non-English queries**.

With `fastembed`, if your document says:
> "A node is a Python function that receives State and returns a partial update."

...and you search with Romanian **"ce este un nod?"** — the model does not understand the connection.  
It was trained only on English. The Romanian words have no meaningful relationship to the English words in the document.  
**Result: wrong or irrelevant chunks are returned.**

With `text-embedding-3-small`, the same Romanian query is embedded in a shared multilingual semantic space.  
"nod" and "node" point to nearby vectors — the model understands they mean the same thing.  
**Result: correct English chunks are returned for a Romanian question — and the LLM answers in Romanian.**

This is called **cross-lingual retrieval** — query in one language, documents in another.

---

### When to use each

| Situation | Use this |
|---|---|
| Prototype — local machine, no internet, no API key | `fastembed` |
| Documents are English only, users query in English | `fastembed` |
| Users may query in any language | `text-embedding-3-small` |
| Production system — higher accuracy required | `text-embedding-3-small` |
| You already have LiteLLM proxy set up | `text-embedding-3-small` — zero extra cost in setup |
| Strict offline / air-gapped environment | `fastembed` |

> **This agent uses `text-embedding-3-small`** — same proxy, same API key, better quality, multilingual.  
> The only code change from `fastembed` is: swap the import, update `EMBEDDING_DIM = 1536`, and pass `base_url` + `api_key`.

## Dependencies
```
qdrant-client>=1.9.0
langchain-qdrant>=0.1.0
langchain-community>=0.3.0
pypdf>=4.0.0
langchain-openai>=0.3.0
```
All already in `requirements.txt`. Install with:
```bash
uv pip install -r requirements.txt
```

## Project structure — files for this agent

```
src/
├── agents/
│   └── rag_agent.py       ← the active agent (registered in Studio)
└── data/
    └── langgraph_concepts.txt  ← demo document indexed by the agent

labs/10-rag-agent/
├── INSTRUCTIONS.md        ← this file
└── solution/
    ├── rag_agent.py       ← reference solution
    └── data/
        └── langgraph_concepts.txt  ← demo document (copy of src/data/)
```

---


## How to build this agent

### STEP 1  Create the agent file
Create this file and leave it completely empty:
**Path:** `src/agents/rag_agent.py`

> Ensure src/data/langgraph_concepts.txt exists (it ships with the project).

### STEP 2  Build in Learn Mode
Type this in GitHub Copilot Chat:
```
Learn Mode  I want to build 10 RAG Agent
```
Copilot will guide you block by block through each section below.

### STEP 3  Test in Studio
```powershell
python studio.py
```
Select **RAG Agent** from the dropdown.

---

## Code structure — block by block

### Block 1 — Docstring
```python
"""
Agent 10 — RAG Agent
Pattern: Retrieval-Augmented Generation (RAG) pipeline.
Teaches: document loading, embedding, Qdrant in-memory vector store,
         semantic search, context-augmented LLM response.

Flow:
  user query
    → node_retrieve: embed query → search Qdrant → top-K chunks
    → node_generate: LLM receives query + context → answer
"""
```
─────────────────────────────────────────────────────────────────────────────
- Documents the agent number, pattern, what it teaches, and the full execution flow
- The Flow section maps directly to the graph edges

### Block 2 — Imports
```python
from pathlib import Path
from typing import TypedDict

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from langgraph.graph import StateGraph, START, END

from src.config import LLM_MODEL, LLM_PROXY, LLM_API_KEY, langfuse_handler
```
─────────────────────────────────────────────────────────────────────────────
- `OpenAIEmbeddings` — from `langchain_openai`, same package as `ChatOpenAI`. Uses the same proxy.
- `DirectoryLoader`, `TextLoader` — load all `.txt` files from a folder
- `RecursiveCharacterTextSplitter` — splits documents into chunks
- `QdrantVectorStore`, `QdrantClient` — vector database interface
- `Distance`, `VectorParams` — Qdrant collection configuration
- No `fastembed` import — `OpenAIEmbeddings` replaces it entirely

### Block 3 — Contract vars + constants
```python
AGENT_NAME = "RAG Agent"
AGENT_TYPE = "chat"
AGENT_DESCRIPTION = "RAG pipeline — loads documents from src/data/, indexes them in Qdrant in-memory, retrieves relevant chunks, and answers using context-augmented LLM response."

trace_log: list[dict] = []

DOCS_PATH = Path(__file__).parent.parent / "data"
COLLECTION_NAME = "rag_docs"
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536
```
─────────────────────────────────────────────────────────────────────────────
- `DOCS_PATH` — resolves to `src/data/` relative to the agent file location (`src/agents/rag_agent.py → src/data/`)
- `EMBEDDING_MODEL = "text-embedding-3-small"` — the model name sent to LiteLLM proxy
- `EMBEDDING_DIM = 1536` — **must match the model**. `text-embedding-3-small` produces 1536-dimension vectors.
  If you switch to `fastembed`, you must change this to `384` — otherwise Qdrant will reject all vectors.

### Block 4 — SYSTEM_PROMPT
```python
SYSTEM_PROMPT = """
You are RAG Agent — the tenth agent in the LangGraph learning series.
...
IMPORTANT: Answer ONLY based on the provided context.
If the context does not contain enough information to answer — say so clearly.
Do not invent facts. Do not use prior knowledge outside the context.
Only answer questions related to the indexed documents, RAG concepts, or the LangGraph learning series.
If the user asks about anything else — politely decline and redirect them to the topics above.
"""
```
─────────────────────────────────────────────────────────────────────────────
- The `IMPORTANT` section is critical — without it the LLM answers from memory, not from documents
- Forces grounding: the LLM must say "I don't know" if the context doesn't contain the answer

### Block 5 — LLM + embeddings + Qdrant initialization
```python
llm = ChatOpenAI(model=LLM_MODEL, base_url=LLM_PROXY, api_key=LLM_API_KEY, temperature=0.3)

embeddings = OpenAIEmbeddings(
    model=EMBEDDING_MODEL,
    base_url=LLM_PROXY,
    api_key=LLM_API_KEY,
)

qdrant_client = QdrantClient(":memory:")
qdrant_client.create_collection(
    collection_name=COLLECTION_NAME,
    vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
)

vector_store = QdrantVectorStore(
    client=qdrant_client,
    collection_name=COLLECTION_NAME,
    embedding=embeddings,
)
```
─────────────────────────────────────────────────────────────────────────────
- `temperature=0.3` — lower than default (0.7). RAG requires precision, not creativity.
- `OpenAIEmbeddings` uses the **same `LLM_PROXY` and `LLM_API_KEY`** as ChatOpenAI — zero extra configuration.
  Internally, it calls `POST /v1/embeddings` on the LiteLLM proxy, which forwards to the real embedding endpoint.
- `QdrantClient(":memory:")` — in-memory mode, no server needed, resets on restart.
- `Distance.COSINE` — measures angle between vectors, standard for semantic text search.
- `VectorParams(size=EMBEDDING_DIM, ...)` — Qdrant must know the vector size upfront. `1536` for this model.
- All three objects (`embeddings`, `qdrant_client`, `vector_store`) are module-level singletons — created once.

> **How it differs from fastembed:**
> ```python
> # fastembed (old)
> embeddings = FastEmbedEmbeddings(model_name="BAAI/bge-small-en-v1.5")
>
> # OpenAI (current)
> embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL, base_url=LLM_PROXY, api_key=LLM_API_KEY)
> ```
> That is the **only line that changes**. The rest of the RAG pipeline — Qdrant, chunking, retrieval — is identical.

### Block 6 — `build_vector_store()`
```python
def build_vector_store() -> None:
    if not DOCS_PATH.exists():
        return
    loader = DirectoryLoader(str(DOCS_PATH), glob="**/*.txt", loader_cls=TextLoader, ...)
    docs = loader.load()
    if not docs:
        return
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_documents(docs)
    vector_store.add_documents(chunks)
```
─────────────────────────────────────────────────────────────────────────────
- Loads all `.txt` files from `src/data/` recursively
- `chunk_size=500` — each chunk is max 500 characters
- `chunk_overlap=50` — last 50 chars of each chunk repeat in the next — prevents cutting ideas mid-sentence
- `add_documents` embeds each chunk and stores it in Qdrant

### Block 7 — State + `node_retrieve`
```python
class State(TypedDict):
    query: str
    context: str
    answer: str

def node_retrieve(state: State) -> dict:
    results = vector_store.similarity_search(state["query"], k=3)
    context = "\n\n".join(doc.page_content for doc in results)
    return {"context": context}
```
─────────────────────────────────────────────────────────────────────────────
- `State` has 3 fields — no `messages` list, this is not a chat agent
- `similarity_search(query, k=3)` — returns top 3 chunks most semantically similar to the query
- Returns only `{"context": ...}` — partial state update

### Block 8 — `node_generate`
```python
def node_generate(state: State) -> dict:
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"Context:\n{state['context']}\n\nQuestion: {state['query']}"),
    ]
    response = llm.invoke(messages, config={"callbacks": [langfuse_handler]})
    return {"answer": response.content or ""}
```
─────────────────────────────────────────────────────────────────────────────
- The HumanMessage contains BOTH the context and the question — this is the augmentation
- LLM sees: retrieved document chunks + user question together
- Returns only `{"answer": ...}` — partial state update

### Block 9 — `build_graph()` + `_graph`
```python
def build_graph():
    g = StateGraph(State)
    g.add_node("retrieve", node_retrieve)
    g.add_node("generate", node_generate)
    g.add_edge(START, "retrieve")
    g.add_edge("retrieve", "generate")
    g.add_edge("generate", END)
    return g.compile()

_graph = build_graph()
```
─────────────────────────────────────────────────────────────────────────────
- Simplest two-node linear graph: `START → retrieve → generate → END`
- No branching, no loop, no tools — fully deterministic
- Compiled once at module load — reused on every `run_agent()` call

### Block 10 — `run_agent()`
```python
def run_agent(payload: str) -> str:
    trace_log.clear()
    build_vector_store()
    result = _graph.invoke({"query": payload, "context": "", "answer": ""})
    return result["answer"]
```
─────────────────────────────────────────────────────────────────────────────
- `build_vector_store()` called on every request — picks up new documents added to `src/data/` without restart
- State initialized with all 3 fields — `TypedDict` requires all keys to be present
- Returns `result["answer"]` — not `result["messages"][-1].content` like chat agents

---

## Test Checklist — RAG Agent

### Setup
1. Ensure `src/data/langgraph_concepts.txt` exists (it ships with the project)
2. Run Studio: `python studio.py`
3. Select **RAG Agent**

---

### Trace structure — what every run produces

Every query produces exactly **4 trace entries:**

| # | Label | Type | From → To | What it shows |
|---|---|---|---|---|
| 1 | `Retrieve` | `node_exec` | `user → qdrant` | The query sent to Qdrant |
| 2 | `Context` | `tool_result` | `qdrant → llm` | First 200 chars of chunks retrieved |
| 3 | `Generate` | `node_exec` | `llm → user` | The query again (passed into generate node) |
| 4 | `LLM` | `llm_response` | `llm → user` | First 200 chars of the LLM answer |

---

### Tests

| # | Input | Expected output | Trace expected |
|---|---|---|---|
| 1 | `"What is a node in LangGraph?"` | Answer grounded in the document — mentions Python function, State, partial update | `node_exec` (Retrieve) → `tool_result` (Context, English chunks) → `node_exec` (Generate) → `llm_response` (LLM, factual answer) |
| 2 | `"ce este un nod in LangGraph?"` *(Romanian)* | Answer **in Romanian** using English context chunks | `node_exec` (Retrieve) → `tool_result` (Context, **English** chunks despite Romanian query) → `node_exec` (Generate) → `llm_response` (Romanian answer) |
| 3 | `"What is the capital of France?"` | LLM says it cannot answer — does **not** hallucinate "Paris" | `node_exec` (Retrieve) → `tool_result` (Context, irrelevant chunks) → `node_exec` (Generate) → `llm_response` (refusal) |
| 4 | `"qu'est-ce qu'un outil dans LangGraph?"` *(French)* | Answer **in French** using English context chunks | `node_exec` (Retrieve) → `tool_result` (Context, English tool/decorator chunks) → `node_exec` (Generate) → `llm_response` (French answer) |

**Why test #1:** The smoke test — confirms the basic RAG pipeline: Qdrant retrieves relevant chunks and the LLM uses them to answer. If this fails, check `DOCS_PATH` and `src/data/langgraph_concepts.txt`.

**Why test #2:** The key multilingual test — `text-embedding-3-small` maps Romanian and English to the same semantic space, so a Romanian query retrieves English chunks. The LLM then responds in Romanian. This would completely fail with `fastembed` (no cross-language vector alignment).

**Why test #3:** The grounding test — verifies the `SYSTEM_PROMPT` constraint ("only answer from the provided context"). If the agent answers "Paris", the system prompt is not working and the LLM falls back to its training data.

**Why test #4:** Confirms multilingual support extends beyond one language pair. `text-embedding-3-small` handles 100+ languages in the same shared vector space. A French query correctly retrieves English tool documentation.

---

### fastembed vs text-embedding-3-small comparison

| Test | fastembed result | text-embedding-3-small result |
|---|---|---|
| English query → English doc | ✅ Works | ✅ Works |
| Romanian query → English doc | ❌ Wrong chunks retrieved | ✅ Correct chunks — answers in Romanian |
| French query → English doc | ❌ Wrong chunks retrieved | ✅ Correct chunks — answers in French |
| Off-topic question | ✅ Refuses (grounding works) | ✅ Refuses (grounding works) |
