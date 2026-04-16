"""
RAGAS evaluation script  runs automatically on all RAG agents found in Langfuse.

Usage:
    python scripts/run_ragas_all.py
    python scripts/run_ragas_all.py --limit 20
    python scripts/run_ragas_all.py --tags hr-assistant            # force specific tag (optional override)
    python scripts/run_ragas_all.py --skip rag-agent-test          # skip specific tags
"""
import sys
import os
import re
import json
import argparse
import requests
from dotenv import load_dotenv

# Load .env from project root
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

#  Config from environment 

_LANGFUSE_HOST  = os.environ.get("LANGFUSE_PROXY", os.environ.get("LANGFUSE_HOST", ""))
_LANGFUSE_PK    = os.environ.get("LANGFUSE_PUBLIC_KEY", "")
_LANGFUSE_SK    = os.environ.get("LANGFUSE_SECRET_KEY", "")
_LLM_PROXY      = os.environ.get("LLM_PROXY", "")
_LLM_API_KEY    = os.environ.get("LLM_API_KEY", "openai")
_AUTH           = (_LANGFUSE_PK, _LANGFUSE_SK)

JUDGE_MODEL     = "gpt-5.4-nano"
_FRAMEWORK_TAGS = {"rag", "rag-synthesise", "rag-classify", "rag-retrieve"}

_llm_judge = ChatOpenAI(
    model=JUDGE_MODEL,
    base_url=_LLM_PROXY,
    api_key=_LLM_API_KEY,
    temperature=0.0,
    request_timeout=30,  # fail fast if LLM proxy is unresponsive
)

#  Judge prompts 

_FAITHFULNESS_PROMPT = """You are an evaluation judge. Assess whether the ANSWER is faithful to the CONTEXT.
Faithful means: every claim in the answer is supported by the context. No hallucinations.

QUESTION: {question}
CONTEXT: {context}
ANSWER: {answer}

Respond ONLY with valid JSON: {{"score": <0.0-1.0>, "reason": "<one sentence>"}}"""

_RELEVANCY_PROMPT = """You are an evaluation judge. Assess whether the ANSWER is relevant to the QUESTION.
Relevant means: the answer directly addresses what was asked, without unnecessary tangents.

QUESTION: {question}
ANSWER: {answer}

Respond ONLY with valid JSON: {{"score": <0.0-1.0>, "reason": "<one sentence>"}}"""

_PRECISION_PROMPT = """You are an evaluation judge. Assess whether the CONTEXT chunks are relevant to the QUESTION.
Precision measures: what fraction of the retrieved chunks are actually useful for answering?

QUESTION: {question}
CONTEXT: {context}

Respond ONLY with valid JSON: {{"score": <0.0-1.0>, "reason": "<one sentence>"}}"""

_GROUND_TRUTH_PROMPT = """Given a QUESTION and REFERENCE DOCUMENT, write the ideal ground truth answer.

QUESTION: {question}
DOCUMENT CONTEXT: {context}

Respond ONLY with valid JSON: {{"ground_truth": "<ideal answer in 1-3 sentences>"}}"""

_RECALL_PROMPT = """Assess whether the CONTEXT contains all information needed to produce the GROUND TRUTH answer.

QUESTION: {question}
GROUND TRUTH: {ground_truth}
CONTEXT: {context}

Respond ONLY with valid JSON: {{"score": <0.0-1.0>, "reason": "<one sentence>"}}"""


#  LLM judge 

def _judge(prompt: str) -> dict | None:
    """Returns None on error/timeout so the trace is skipped, not scored 0."""
    try:
        response = _llm_judge.invoke([
            SystemMessage(content="You are a precise evaluation judge. Respond only with valid JSON."),
            HumanMessage(content=prompt),
        ])
        text = (response.content or "").strip()
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            return json.loads(m.group(0))
        return None
    except Exception:
        return None


#  Langfuse REST helpers 

def _fetch_agent_tags(limit: int = 100) -> list[str]:
    """Discover RAG agent tags from traces tagged with rag."""
    url = f"{_LANGFUSE_HOST}/api/public/traces?limit={limit}&tags=rag"
    try:
        r = requests.get(url, auth=_AUTH, timeout=15)
        r.raise_for_status()
        seen: list[str] = []
        for t in r.json().get("data", []):
            for tag in t.get("tags", []):
                if tag not in _FRAMEWORK_TAGS and tag not in seen:
                    seen.append(tag)
        return seen
    except Exception as exc:
        print(f"  [!] Failed to fetch tags: {exc}")
        return []


def _fetch_traces(tag: str, limit: int) -> list[dict]:
    url = f"{_LANGFUSE_HOST}/api/public/traces?limit={limit}&tags={tag}"
    try:
        r = requests.get(url, auth=_AUTH, timeout=15)
        r.raise_for_status()
        return r.json().get("data", [])
    except Exception as exc:
        print(f"  [!] Failed to fetch traces for '{tag}': {exc}")
        return []


def _fetch_observations(trace_id: str) -> list[dict]:
    url = f"{_LANGFUSE_HOST}/api/public/traces/{trace_id}"
    try:
        r = requests.get(url, auth=_AUTH, timeout=15)
        r.raise_for_status()
        return r.json().get("observations", [])
    except Exception:
        return []


def _push_score(trace_id: str, name: str, value: float, comment: str = "") -> None:
    url = f"{_LANGFUSE_HOST}/api/public/scores"
    payload = {"traceId": trace_id, "name": name, "value": round(value, 4), "dataType": "NUMERIC"}
    if comment:
        payload["comment"] = comment
    try:
        requests.post(url, auth=_AUTH, json=payload, timeout=10)
    except Exception:
        pass


#  Trace parsing 

def _extract_qa(trace: dict, observations: list[dict]) -> dict | None:
    messages = []
    for obs in observations:
        inp = obs.get("input")
        if isinstance(inp, list) and len(inp) > len(messages):
            messages = inp

    if not messages:
        return None

    last_user_idx = -1
    for i, msg in enumerate(messages):
        if isinstance(msg, dict) and msg.get("role") == "user":
            last_user_idx = i

    if last_user_idx == -1:
        return None

    question = messages[last_user_idx].get("content", "")
    if not question:
        return None

    context_chunks = []
    for msg in messages[last_user_idx + 1:]:
        if isinstance(msg, dict) and msg.get("role") == "tool":
            content = msg.get("content", "")
            if isinstance(content, str) and len(content) > 50 and not content.strip().startswith("{"):
                context_chunks.append(content)

    out = trace.get("output", {})
    answer = out.get("content", "") if isinstance(out, dict) else (out if isinstance(out, str) else "")

    if not answer or not context_chunks:
        return None

    return {
        "question": question.strip(),
        "context": "\n\n---\n\n".join(context_chunks),
        "answer": answer.strip(),
    }


#  Per-trace evaluation 

def _evaluate_trace(trace_id: str, qa: dict, agent_tag: str) -> dict:
    q   = qa["question"]
    ctx = qa["context"][:3000]
    ans = qa["answer"][:1500]

    f_result  = _judge(_FAITHFULNESS_PROMPT.format(question=q, context=ctx, answer=ans))
    r_result  = _judge(_RELEVANCY_PROMPT.format(question=q, answer=ans))
    p_result  = _judge(_PRECISION_PROMPT.format(question=q, context=ctx))
    gt_result = _judge(_GROUND_TRUTH_PROMPT.format(question=q, context=ctx))

    # Skip trace entirely if any judge call failed — no fake 0.0 scores
    if not f_result or not r_result or not p_result or not gt_result:
        return None

    ground_truth = gt_result.get("ground_truth", "")
    if ground_truth:
        rc_result = _judge(_RECALL_PROMPT.format(question=q, ground_truth=ground_truth, context=ctx))
    else:
        rc_result = None

    if not rc_result:
        return None

    faithfulness      = float(f_result.get("score", 0.0))
    answer_relevancy  = float(r_result.get("score", 0.0))
    context_precision = float(p_result.get("score", 0.0))
    context_recall    = float(rc_result.get("score", 0.0))

    _push_score(trace_id, f"{agent_tag}:faithfulness",      faithfulness,      f_result.get("reason", ""))
    _push_score(trace_id, f"{agent_tag}:answer_relevancy",  answer_relevancy,  r_result.get("reason", ""))
    _push_score(trace_id, f"{agent_tag}:context_precision", context_precision, p_result.get("reason", ""))
    _push_score(trace_id, f"{agent_tag}:context_recall",    context_recall,    rc_result.get("reason", ""))

    return {
        "faithfulness": faithfulness,
        "answer_relevancy": answer_relevancy,
        "context_precision": context_precision,
        "context_recall": context_recall,
    }


#  Evaluate one agent tag 

def evaluate_tag(tag: str, limit: int) -> None:
    print(f"\nEvaluating tag: {tag}")
    traces = _fetch_traces(tag, limit)
    if not traces:
        print("  (no traces found  skipped)")
        return

    results = []
    total = len(traces)
    for idx, t in enumerate(traces, start=1):
        print(f"  working [{idx}/{total}] ...", end="\r", flush=True)
        observations = _fetch_observations(t["id"])
        qa = _extract_qa(t, observations)
        if not qa:
            continue
        result = _evaluate_trace(t["id"], qa, agent_tag=tag)
        if result:
            results.append(result)
    print(" " * 40, end="\r")  # clear the working line

    if not results:
        print("  (no RAG context found in traces  skipped)")
        return

    labels = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
    for label in labels:
        avg = sum(r[label] for r in results) / len(results)
        flag = "ok" if avg >= 0.8 else ("warn" if avg >= 0.6 else "FAIL")
        print(f"  {label:<24} = {avg:.2f}  [{flag}]")
    print(f"  ({len(results)} traces evaluated, scores pushed to Langfuse)")
    print(f"  done ✓")


#  Main 

def main():
    parser = argparse.ArgumentParser(description="RAGAS evaluation for all RAG agents in Langfuse")
    parser.add_argument("--limit", type=int, default=10, help="Traces per agent (default: 10)")
    parser.add_argument("--tags",  type=str, default="", help="Comma-separated tags (new agents, first run)")
    parser.add_argument("--skip",  type=str, default="", help="Comma-separated tags to skip")
    args = parser.parse_args()

    skip_tags = {t.strip() for t in args.skip.split(",") if t.strip()}

    if args.tags:
        tags_to_run = [t.strip() for t in args.tags.split(",") if t.strip()]
        print(f"Using explicit tags: {tags_to_run}")
    else:
        print("Auto-discovering RAG agents from Langfuse...")
        all_tags = _fetch_agent_tags()
        if not all_tags:
            print("No RAG agents found. Use --tags for a new agent:")
            print("  python scripts/run_ragas_all.py --tags hr-assistant")
            sys.exit(1)
        tags_to_run = [t for t in all_tags if t not in skip_tags]
        print(f"Found {len(tags_to_run)} RAG agent(s) to evaluate.")

    for tag in tags_to_run:
        evaluate_tag(tag, args.limit)

    print(f"\nDone. Scores pushed to Langfuse  dashboard updates automatically.")


if __name__ == "__main__":
    main()
