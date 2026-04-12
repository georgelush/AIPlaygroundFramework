"""
Agent 10 — RAG Agent
Pattern: Retrieval-Augmented Generation (RAG) pipeline.
Teaches: document loading, OpenAI embeddings via LiteLLM proxy, Qdrant in-memory vector store,
         cross-lingual semantic search, context-augmented LLM response.

Embedding model: text-embedding-3-small (1536 dims, 100+ languages)
  — query in Romanian, French, or any language → retrieves correct English chunks.

Flow:
  user query (any language)
    → node_retrieve: embed query → similarity_search Qdrant → top-3 chunks (English)
    → node_generate: LLM receives query + English context → answer in user's language
"""

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

AGENT_NAME = "RAG Agent"
AGENT_TYPE = "chat"
AGENT_DESCRIPTION = "RAG pipeline — loads documents from src/data/, indexes them in Qdrant in-memory, retrieves relevant chunks, and answers using context-augmented LLM response."

trace_log: list[dict] = []

DOCS_PATH = Path(__file__).parent.parent / "data"
COLLECTION_NAME = "rag_docs"
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536

SYSTEM_PROMPT = """
You are RAG Agent — the tenth agent in the LangGraph learning series.
Your purpose: demonstrate Retrieval-Augmented Generation — answering questions
using only the context retrieved from indexed documents, not from memory.
Concepts you teach: document loading, embedding, vector search, context augmentation.
If asked who you are or why you exist — explain exactly this.
IMPORTANT: Answer ONLY based on the provided context.
If the context does not contain enough information to answer — say so clearly.
Do not invent facts. Do not use prior knowledge outside the context.
Only answer questions related to the indexed documents, RAG concepts, or the LangGraph learning series.
If the user asks about anything else — politely decline and redirect them to the topics above.
"""


llm = ChatOpenAI(
    model=LLM_MODEL,
    base_url=LLM_PROXY,
    api_key=LLM_API_KEY,
    temperature=0.3,
)

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


def build_vector_store() -> None:
    if not DOCS_PATH.exists():
        return

    loader = DirectoryLoader(
        str(DOCS_PATH),
        glob="**/*.txt",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
    )
    docs = loader.load()
    if not docs:
        return

    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_documents(docs)

    vector_store.add_documents(chunks)


class State(TypedDict):
    query: str
    context: str
    answer: str


def node_retrieve(state: State) -> dict:
    trace_log.append({
        "type": "node_exec",
        "label": "Retrieve",
        "from": "user",
        "to": "qdrant",
        "arrow": "->",
        "content": state["query"][:200],
        "fn": "node_retrieve",
    })

    results = vector_store.similarity_search(state["query"], k=3)
    context = "\n\n".join(doc.page_content for doc in results)

    trace_log.append({
        "type": "tool_result",
        "label": "Context",
        "from": "qdrant",
        "to": "llm",
        "arrow": "->",
        "content": context[:200],
        "fn": "node_retrieve",
    })

    return {"context": context}


def node_generate(state: State) -> dict:
    trace_log.append({
        "type": "node_exec",
        "label": "Generate",
        "from": "llm",
        "to": "user",
        "arrow": "->",
        "content": state["query"][:200],
        "fn": "node_generate",
    })

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"Context:\n{state['context']}\n\nQuestion: {state['query']}"),
    ]

    response = llm.invoke(messages, config={"callbacks": [langfuse_handler]})

    trace_log.append({
        "type": "llm_response",
        "label": "LLM",
        "from": "llm",
        "to": "user",
        "arrow": "->",
        "content": response.content[:200],
        "fn": "node_generate",
    })

    return {"answer": response.content or ""}


def build_graph():
    g = StateGraph(State)
    g.add_node("retrieve", node_retrieve)
    g.add_node("generate", node_generate)
    g.add_edge(START, "retrieve")
    g.add_edge("retrieve", "generate")
    g.add_edge("generate", END)
    return g.compile()


_graph = build_graph()


def run_agent(payload: str) -> str:
    trace_log.clear()
    build_vector_store()
    result = _graph.invoke({"query": payload, "context": "", "answer": ""})
    return result["answer"]
