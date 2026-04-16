"""
src/tools/hr_tools.py — Reusable HR tools for the HR Assistant agent (Lab 20).
These tools are imported by src/nodes/hr_nodes.py and reusable by any future agent.
"""
import uuid as _uuid_module
import re
from collections import Counter
from datetime import datetime, timedelta, date
from pathlib import Path

from langchain_core.tools import tool
from langchain_core.documents import Document
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

# Section separator used in hr_handbook.txt between sections
_SECTION_SEP = "━" * 50

# Parent-child RAG stores:
#   _parent_docs  — parent_id → full section text (used for broad queries)
#   child chunks  — indexed in Qdrant, each tagged with parent_id in metadata
_parent_docs: dict[str, str] = {}


def _split_into_sections(text: str) -> list[str]:
    """Split handbook text on section separators so each section becomes one parent.

    Splits on the pattern: \n━━━\nSECTION TITLE\n━━━\n that surrounds every header.
    Returns a list where each element is one full section (header + all subsections).
    """
    sep = re.escape(_SECTION_SEP)
    # Matches: \n===\nSOME TITLE\n===\n  — captures the title
    pattern = rf"\n{sep}\n([^\n]+)\n{sep}\n"
    parts = re.split(pattern, text)
    sections: list[str] = []
    # parts[0] = preamble text before first section header
    if parts[0].strip():
        sections.append(parts[0].strip())
    # parts[1], parts[2] = title, content; parts[3], parts[4] = next title, content; ...
    for i in range(1, len(parts), 2):
        if i + 1 < len(parts):
            header = parts[i].strip()
            content = parts[i + 1].strip()
            sections.append(f"{header}\n\n{content}")
    return sections

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
    """Load hr_handbook.txt, split into parent sections then child chunks, index children in Qdrant.

    Parent-child RAG strategy:
      - Parent = one full handbook section, parsed with _split_into_sections() (regex-based).
        Stored in _parent_docs dict keyed by section index.
      - Child  = subsection paragraph (~400 chars, chunk_overlap=0).  Indexed in Qdrant
        with 'parent_id' metadata so the parent can be retrieved by section index.

    At query time (search_hr_handbook tool):
      - Cosine similarity scores: 1.0 = perfect match, lower = less relevant.
      - Filter: keep chunks with score >= 0.40 (relevant) and group by parent_id.
      - If >= 2 chunks from same parent have SIMILAR scores (ratio < 1.8) → broad
        section-level query → return full parent section.
      - If top chunk score is >> second score (ratio >= 1.8) → specific subsection
        query → return only the matching child chunks.
    """
    global _indexed
    if _indexed:
        return
    if not HANDBOOK_PATH.exists():
        return
    loader = TextLoader(str(HANDBOOK_PATH), encoding="utf-8")
    docs = loader.load()
    raw_text = docs[0].page_content

    # ── Step 1: parse into one parent per section (regex-based) ──────────────
    sections = _split_into_sections(raw_text)

    # ── Step 2: split each section into child chunks, tag with parent_id ─────
    # chunk_size=400, overlap=0: keeps subsection headers merged with their content.
    child_splitter = RecursiveCharacterTextSplitter(chunk_size=400, chunk_overlap=0)
    all_children: list[Document] = []
    for idx, section_text in enumerate(sections):
        parent_id = f"section_{idx}"
        _parent_docs[parent_id] = section_text
        parent_doc = Document(page_content=section_text)
        children = child_splitter.split_documents([parent_doc])
        for child in children:
            child.metadata["parent_id"] = parent_id
        all_children.extend(children)

    _vector_store.add_documents(all_children)
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
    results = _vector_store.similarity_search_with_score(query, k=6)
    # Cosine similarity scores: 1.0 = perfect match, 0.0 = no match.
    # Keep chunks with similarity >= 0.40 (relevant matches).
    relevant = [(doc, score) for doc, score in results if score >= 0.40]
    if not relevant:
        # Fallback: accept top-2 if they have at least some similarity
        relevant = [(doc, score) for doc, score in results[:2] if score >= 0.30]
    if not relevant:
        return "No relevant information found in the HR handbook."

    # ── Parent-child routing ───────────────────────────────────────────────────
    # CONTACT INFORMATION (section_14) is a directory, not a policy section.
    # Never expand it to full parent — always treat its chunks as specific results.
    # Filter it out of parent_groups before choosing the dominant policy section.
    contact_pid = next(
        (pid for pid, text in _parent_docs.items() if text.startswith("CONTACT INFORMATION")),
        None,
    )

    # Group child hits by their parent section.
    parent_groups: dict[str, list[tuple]] = {}
    for doc, score in relevant:
        pid = doc.metadata.get("parent_id", "unknown")
        parent_groups.setdefault(pid, []).append((doc, score))

    # Separate out contact chunks — they are always supplementary.
    contact_chunks = [
        doc.page_content
        for doc, score in relevant
        if doc.metadata.get("parent_id") == contact_pid
    ]
    policy_groups = {pid: hits for pid, hits in parent_groups.items() if pid != contact_pid}

    if not policy_groups:
        # Query only matched contact information → return contact chunks directly.
        return "\n\n---\n\n".join(contact_chunks) if contact_chunks else "No relevant information found in the HR handbook."

    # Dominant parent = policy section whose best child chunk scores highest.
    dominant_parent = max(policy_groups, key=lambda pid: max(s for _, s in policy_groups[pid]))
    dominant_best_score = max(s for _, s in policy_groups[dominant_parent])
    same_parent_hits = sorted(policy_groups[dominant_parent], key=lambda x: x[1], reverse=True)

    # If dominant policy section scores below 0.50, it's a weak policy match.
    # Skip policy content and return only the contact chunks (pure contact query).
    if dominant_best_score < 0.50:
        if contact_chunks:
            return "\n\n---\n\n".join(contact_chunks)
        return "\n\n---\n\n".join(doc.page_content for doc, _ in same_parent_hits)

    if len(same_parent_hits) >= 2:
        top_score = same_parent_hits[0][1]
        second_score = same_parent_hits[1][1]
        specificity_ratio = top_score / second_score if second_score > 0 else float("inf")

        if specificity_ratio < 1.8:
            # Similar scores across multiple children → broad section-level query
            # → return the full parent section so the LLM has complete context.
            section_text = _parent_docs.get(dominant_parent, "")
            if section_text:
                # Append any contact chunks so the LLM can cite exact addresses/ext.
                if contact_chunks:
                    return section_text + "\n\n---\n\n" + "\n\n---\n\n".join(contact_chunks)
                return section_text

    # Specific subsection query (one child far ahead of others) → return child chunks only.
    # Append contact chunks so the LLM can cite exact email/ext when needed.
    primary_chunks = [doc.page_content for doc, _ in same_parent_hits]
    return "\n\n---\n\n".join(primary_chunks + contact_chunks)



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
