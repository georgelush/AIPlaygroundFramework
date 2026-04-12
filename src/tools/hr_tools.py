"""
src/tools/hr_tools.py — Reusable HR tools for the HR Assistant agent (Lab 20).
These tools are imported by src/nodes/hr_nodes.py and reusable by any future agent.
"""
import uuid as _uuid_module
from datetime import datetime, timedelta, date
from pathlib import Path

from langchain_core.tools import tool
from langchain_openai import OpenAIEmbeddings
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

from src.config import LLM_PROXY, LLM_API_KEY

# ── Vector store setup ─────────────────────────────────────────────────────────

HANDBOOK_PATH = Path(__file__).parent.parent / "data" / "hr_handbook.txt"
COLLECTION_NAME = "hr_handbook"
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536

_embeddings = OpenAIEmbeddings(
    model=EMBEDDING_MODEL,
    base_url=LLM_PROXY,
    api_key=LLM_API_KEY,
)

_qdrant_client = QdrantClient(":memory:")
_qdrant_client.create_collection(
    collection_name=COLLECTION_NAME,
    vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
)

_vector_store = QdrantVectorStore(
    client=_qdrant_client,
    collection_name=COLLECTION_NAME,
    embedding=_embeddings,
)

_indexed = False


def build_vector_store() -> None:
    """Load hr_handbook.txt, split into chunks, and index in Qdrant. Idempotent."""
    global _indexed
    if _indexed:
        return
    if not HANDBOOK_PATH.exists():
        return
    loader = TextLoader(str(HANDBOOK_PATH), encoding="utf-8")
    docs = loader.load()
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_documents(docs)
    _vector_store.add_documents(chunks)
    _indexed = True


# ── DEPRECATED static data (replaced by RAG) ───────────────────────────────────
# Keep this comment so reviewers understand the migration from Lab 20 v1 to v2.


# ── Tools ──────────────────────────────────────────────────────────────────────

@tool
def search_hr_handbook(query: str) -> str:
    """Search the company HR handbook using semantic similarity.
    Use this for any question about company policies, procedures, or employee information:
    vacation days, remote work, benefits, sick leave, working hours, payroll, onboarding,
    equipment requests, IT support, training budget, performance reviews, parking, or expenses.
    Returns the most relevant passages from the official HR handbook."""
    build_vector_store()
    results = _vector_store.similarity_search(query, k=3)
    if not results:
        return "No relevant information found in the HR handbook."
    return "\n\n---\n\n".join(doc.page_content for doc in results)


@tool
def calculate_leave_days(start_date: str, end_date: str) -> str:
    """Calculates the number of working days (Monday–Friday) between two dates, inclusive.
    Use this when the employee asks how many leave days a specific period requires.
    Dates must be in YYYY-MM-DD format. Example: start_date='2026-06-01', end_date='2026-06-05'."""
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        if end < start:
            return "Error: end_date must be after or equal to start_date."
        working_days = 0
        current = start
        while current <= end:
            if current.weekday() < 5:
                working_days += 1
            current += timedelta(days=1)
        return f"Working days from {start_date} to {end_date}: {working_days} day(s)."
    except ValueError:
        return "Error: dates must be in YYYY-MM-DD format (e.g. 2026-06-01)."


@tool
def submit_vacation_request(start_date: str, end_date: str) -> str:
    """Submit a vacation request for HR approval.
    Use this ONLY when the employee explicitly wants to request, book, or submit vacation days.
    Do NOT use this just for questions about vacation policy — use search_hr_handbook for those.
    Dates must be in YYYY-MM-DD format. Example: start_date='2026-06-01', end_date='2026-06-05'.
    The request will be reviewed by HR before being approved or rejected."""
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        today = date.today()

        if end < start:
            return "Error: end_date must be after or equal to start_date."

        notice_days = (start.date() - today).days
        if notice_days < 14:
            days_short = 14 - notice_days
            return (
                f"Error: Leave must be requested at least 2 weeks in advance. "
                f"Your request starts in {notice_days} day(s) — "
                f"please submit at least {days_short} more day(s) earlier."
            )

        working_days = 0
        current = start
        while current <= end:
            if current.weekday() < 5:
                working_days += 1
            current += timedelta(days=1)

        return (
            f"VACATION REQUEST\n"
            f"REQUEST_ID: REQ-{_uuid_module.uuid4().hex[:8].upper()}\n"
            f"Period: {start_date} -> {end_date}\n"
            f"Working days: {working_days}\n"
            f"Advance notice: {notice_days} calendar days\n"
            f"Status: PENDING HR APPROVAL"
        )
    except ValueError:
        return "Error: dates must be in YYYY-MM-DD format (e.g. 2026-06-01)."


# ── Tool list ──────────────────────────────────────────────────────────────────

TOOLS = [search_hr_handbook, calculate_leave_days, submit_vacation_request]
