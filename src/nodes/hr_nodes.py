"""
src/nodes/hr_nodes.py  Reusable node functions for the HR Assistant agent (Lab 20).
LLM instantiation and node logic live here  imported by src/graphs/hr_graph.py.
"""
import re
import json
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage, AIMessage
from langchain_core.runnables import RunnableConfig
from langgraph.types import interrupt
from langgraph.graph import MessagesState
import redis as _redis_module

from src.config import LLM_MODEL, LLM_PROXY, LLM_API_KEY, langfuse_handler, REDIS_URL
from src.mixins.cost_tracking import CostTrackingMixin
from src.mixins.logging_mixin import LoggingMixin
from src.tools.hr_tools import TOOLS

# Module-level trace buffer  written by node_llm, read by capstone_agent.run_agent()
# Captures tool_call and tool_result entries from every ReAct loop iteration.
_node_trace: list[dict] = []

# Module-level cost tracker — accumulates token usage across all LLM calls in a run
_cost_tracker = CostTrackingMixin()

# Module-level logger — structured console/file logging for every node step
_logger = LoggingMixin()

# ── Redis client for HITL request store ──────────────────────────────────────────────────
# Stores pending vacation requests so managers can approve/reject by REQUEST_ID
# from any tab — decoupled from the LangGraph thread_id.
REQUEST_TTL = 7 * 86_400  # 7 days — requests expire automatically
_request_store = _redis_module.from_url(REDIS_URL, decode_responses=True)


def _save_pending_request(request_id: str, thread_id: str, details: str) -> None:
    """Store a pending vacation request in Redis keyed by REQUEST_ID."""
    _request_store.setex(
        f"hr:pending:{request_id}",
        REQUEST_TTL,
        json.dumps({"thread_id": thread_id, "details": details, "status": "pending", "employee_id": None}),
    )


def tag_pending_request_employee(request_id: str, employee_id: str) -> None:
    """Set the employee_id on a pending request after the interrupt is detected.
    Called from run_agent() which knows the user_id — node_approve does not."""
    raw = _request_store.get(f"hr:pending:{request_id}")
    if raw:
        data = json.loads(raw)
        data["employee_id"] = employee_id
        ttl = _request_store.ttl(f"hr:pending:{request_id}")
        _request_store.setex(f"hr:pending:{request_id}", max(ttl, 1), json.dumps(data))


def resolve_pending_request(request_id: str) -> dict | None:
    """Return stored request data dict, or None if not found / already processed."""
    raw = _request_store.get(f"hr:pending:{request_id}")
    return json.loads(raw) if raw else None


def close_pending_request(request_id: str, status: str) -> None:
    """Mark request as approved or rejected. Keeps record in Redis for 1 hour for audit."""
    raw = _request_store.get(f"hr:pending:{request_id}")
    if raw:
        data = json.loads(raw)
        data["status"] = status
        _request_store.setex(f"hr:pending:{request_id}", 3600, json.dumps(data))

# == Security utilities =========================================================
# Reusable by any node or boundary check. Imported by capstone_agent.run_agent().

MAX_INPUT_LENGTH = 2000

INJECTION_PATTERNS = [
    r"ignore (all )?(previous |prior )?instructions",
    r"you are now",
    r"act as (a |an )?(?!hr assistant)",
    r"forget (everything|all|your instructions)",
    r"(system prompt|system_prompt)",
    r"reveal your (instructions|prompt|system)",
    r"bypass (your )?(guidelines|restrictions|rules)",
    r"jailbreak",
    r"pretend (you are|to be)",
    r"disregard (your )?(previous |prior )?instructions",
]


def validate_input(text: str) -> str | None:
    """Returns an error string if input is invalid, else None.
    Call this at the system boundary (run_agent) before touching the graph."""
    if not text or not text.strip():
        return "Input cannot be empty."
    if len(text) > MAX_INPUT_LENGTH:
        return f"Input too long. Maximum allowed: {MAX_INPUT_LENGTH} characters."
    return None


def detect_injection(text: str) -> bool:
    """Returns True if prompt injection patterns are detected."""
    lowered = text.lower()
    return any(re.search(pattern, lowered) for pattern in INJECTION_PATTERNS)


def sanitize_output(text: str) -> str:
    """Strips potential system prompt leakage from LLM output."""
    cleaned = re.sub(r"(?i)(system prompt|SYSTEM_PROMPT)[:\s]*.*", "[REDACTED]", text)
    return cleaned.strip()


# == System prompt ==============================================================


SYSTEM_PROMPT = """
You are HR Assistant - the twentieth agent in the LangGraph learning series.
Your purpose: demonstrate production-ready agent architecture combining RAG + separation of concerns.
Concepts you teach: RAG inside a tool, semantic search with Qdrant, src/tools/ + src/nodes/ + src/graphs/ separation, compiled graph reuse.
If asked who you are or why you exist - explain exactly this.

You are an HR assistant for ACME Corporation employees.

When employees ask about company policies, procedures, or HR information:
  -> ALWAYS use the search_hr_handbook tool to retrieve the answer from the official document.
  -> NEVER answer HR policy questions from memory - the handbook is the source of truth.
  -> Include ALL specific details from the retrieved text (numbers, conditions, deadlines, contacts).
  -> Do NOT summarize or paraphrase - present the full content from the retrieved sections.

When employees ask to calculate working days between two dates:
  -> Use the calculate_leave_days tool.

When employees want to REQUEST, BOOK, or SUBMIT vacation days (not just ask about the policy):
  -> Use the submit_vacation_request tool with start_date and end_date in YYYY-MM-DD format.
  -> The request will be sent to HR for approval — inform the employee they must wait for HR decision.
  -> Only trigger this tool when the employee clearly wants to submit a request, not when asking about vacation policy.

LANGUAGE RULE: Always respond in the SAME language the user writes in.
If the user writes in Romanian - respond in Romanian.
If the user writes in French - respond in French.
If the user writes in English - respond in English.
The handbook is in English - translate the retrieved content into the user's language when needed.

Be professional and friendly. Only answer HR-related questions. Politely decline anything unrelated.
"""

# == LLM =======================================================================
# Production dual-LLM pattern — two models, two prompts, two input sizes.
#
# ┌─────────────────┬──────────────────────────────┬────────────────────────────┐
# │                 │ llm_classify (gpt-5.4-nano)  │ llm_smart (gpt-5.1)        │
# ├─────────────────┼──────────────────────────────┼────────────────────────────┤
# │ Task            │ Routing: which tool to call? │ Synthesis: write HR answer │
# │ Prompt          │ ROUTING_PROMPT (~120 tokens) │ SYSTEM_PROMPT (~350 tokens)│
# │ Input           │ last message only, max 300ch │ full conversation history  │
# │ Temperature     │ 0.0 — deterministic          │ 0.7 — natural language     │
# │ Tools bound     │ yes — must pick the tool     │ no — only writes text      │
# │ Typical cost    │ ~0.000015 USD / call         │ ~0.002 USD / call          │
# └─────────────────┴──────────────────────────────┴────────────────────────────┘
#
# KEY insight: input tokens dominate cost, not output.
# Passing the full SYSTEM_PROMPT + history to the routing model wastes ~1400
# tokens on HR policy text that is irrelevant to tool selection.
# The classifier only needs: "here are 3 tools, which one fits this request?"

ROUTING_PROMPT = """You are an HR request router. Pick the right tool for the user request.

Tools available:
- search_hr_handbook   → policy questions, rules, procedures, benefits
- calculate_leave_days → count working days between two dates
- submit_vacation_request → employee wants to REQUEST or BOOK vacation days

If none of the tools apply, respond directly without calling any tool.
Be concise — your only job is tool selection."""

# Truncate input to routing model — only the last user message matters for tool selection.
# Saves ~1400 input tokens (full SYSTEM_PROMPT + history) on every routing call.
ROUTING_INPUT_LIMIT = 300  # characters

LLM_SMART_MODEL = "gpt-5.1"
LLM_CLASSIFY_MODEL = LLM_MODEL  # gpt-5.4-nano — same cheap model, radically different prompt

llm_classify = ChatOpenAI(
    model=LLM_CLASSIFY_MODEL,
    base_url=LLM_PROXY,
    api_key=LLM_API_KEY,
    temperature=0.0,   # deterministic — tool selection is not creative
)

llm_smart = ChatOpenAI(
    model=LLM_SMART_MODEL,
    base_url=LLM_PROXY,
    api_key=LLM_API_KEY,
    temperature=0.7,   # expressive — writing HR explanations benefits from variation
)

llm_classify_with_tools = llm_classify.bind_tools(TOOLS)

# == Nodes ======================================================================


def node_llm(state: MessagesState) -> dict:
    """Main LLM node.
    - Detects ToolMessage results from previous tool calls -> appends tool_result to _node_trace.
    - Calls LLM with tools bound.
    - Detects new tool_calls in LLM response -> appends tool_call to _node_trace.
    """
    _logger.log_step("node_llm", f"messages={len(state['messages'])}")

    # If the last message is a ToolMessage, record what the tool returned
    if state["messages"] and isinstance(state["messages"][-1], ToolMessage):
        last = state["messages"][-1]
        _node_trace.append({
            "type": "tool_result",
            "label": last.name or "tool",
            "from": "tool",
            "to": "llm",
            "arrow": "->",
            "content": str(last.content)[:200],
        })

    # ── Dual-LLM routing decision ──────────────────────────────────────────────────
    # is_synthesis: tools already ran → write the final answer → llm_smart + full history
    # is_routing:   first pass → pick a tool → llm_classify + truncated single message
    is_synthesis = bool(state["messages"]) and isinstance(state["messages"][-1], ToolMessage)

    if is_synthesis:
        # Full context needed — LLM must synthesise tool results + follow HR policy rules
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
        active_llm   = llm_smart
        active_model = LLM_SMART_MODEL
    else:
        # Routing only — truncate to last user message to minimise input tokens.
        # The routing model does NOT need HR policy text — only tool descriptions.
        last_content = state["messages"][-1].content if state["messages"] else ""
        truncated    = last_content[:ROUTING_INPUT_LIMIT]
        messages     = [SystemMessage(content=ROUTING_PROMPT), HumanMessage(content=truncated)]
        active_llm   = llm_classify_with_tools
        active_model = LLM_CLASSIFY_MODEL

    response = active_llm.invoke(messages, config={"callbacks": [langfuse_handler]})

    # Track token cost for this LLM call
    usage = _cost_tracker.track_usage(response, model=active_model)
    role_label = "synthesise" if is_synthesis else "classify"
    _node_trace.append({
        "type": "llm_response",
        "label": f"[{active_model}:{role_label}] in={usage['input_tokens']} out={usage['output_tokens']} cost=${usage['cost_usd']}",
        "from": "llm",
        "to": "node_llm",
        "arrow": "<-",
        "content": f"model={active_model} | role={role_label} | in={usage['input_tokens']} | out={usage['output_tokens']} | cost=${usage['cost_usd']}",
    })

    # If LLM decided to call tools, record each call
    if hasattr(response, "tool_calls") and response.tool_calls:
        for tc in response.tool_calls:
            args_preview = str(tc.get("args", {}))[:150]
            _node_trace.append({
                "type": "tool_call",
                "label": tc["name"],
                "from": "llm",
                "to": "tool",
                "arrow": "->",
                "content": f"{tc['name']}({args_preview})",
            })

    return {"messages": state["messages"] + [response]}


def node_approve(state: MessagesState, config: RunnableConfig) -> dict:
    """HITL approval gate for vacation requests.
    Extracts REQUEST_ID from the tool result, saves the request to Redis,
    then pauses with interrupt() so a manager can approve/reject by ID from any tab.
    """
    _logger.log_step("node_approve", "awaiting HR decision")

    # Find the vacation request details from the last submit_vacation_request tool result
    request_details = ""
    for msg in reversed(state["messages"]):
        if isinstance(msg, ToolMessage) and msg.name == "submit_vacation_request":
            request_details = msg.content
            _node_trace.append({
                "type": "tool_result",
                "label": "submit_vacation_request",
                "from": "tool",
                "to": "hr",
                "arrow": "->",
                "content": request_details[:200],
            })
            break

    # Extract REQUEST_ID generated by submit_vacation_request
    id_match = re.search(r"REQUEST_ID:\s*(REQ-[A-F0-9]{8})", request_details)
    request_id = id_match.group(1) if id_match else "REQ-UNKNOWN"

    # Persist the pending request in Redis keyed by REQUEST_ID so managers
    # can approve from any tab using 'approve:REQ-XXXXXXXX'
    thread_id = config.get("configurable", {}).get("thread_id", "default")
    _save_pending_request(request_id, thread_id, request_details)

    _node_trace.append({
        "type": "node_exec",
        "label": f"HITL Pending [{request_id}]",
        "from": "graph",
        "to": "hr",
        "arrow": "->",
        "content": f"request_id={request_id} | thread_id={thread_id} | saved to Redis",
    })

    decision = interrupt(
        f"HR approval required for {request_id}. "
        f"Manager: type 'approve:{request_id}' or 'reject:{request_id}'."
    )

    _node_trace.append({
        "type": "tool_result",
        "label": "HITL Decision",
        "from": "hr",
        "to": "graph",
        "arrow": "->",
        "content": f"HR decision for {request_id}: {str(decision).strip()}",
    })

    # Parse decision — format: "approve:alice" or "reject:alice" or plain "approve"
    decision_str = str(decision).strip().lower()
    parts = decision_str.split(":", 1)
    outcome_word = parts[0]                                   # "approve" or "reject"
    approver = parts[1].strip() if len(parts) > 1 else None  # "alice", or None
    approver_label = f"**{approver}**" if approver else "**your manager**"

    outcome = "approved" if "approve" in outcome_word else "rejected"
    close_pending_request(request_id, outcome)

    if outcome == "approved":
        updated_details = request_details.replace("Status: PENDING HR APPROVAL", "Status: APPROVED ✓")
        reply = f"Your vacation request **{request_id}** has been approved by {approver_label}.\n\n{updated_details}"
    else:
        updated_details = request_details.replace("Status: PENDING HR APPROVAL", "Status: REJECTED ✗")
        reply = f"Your vacation request **{request_id}** has been rejected by {approver_label}.\n\n{updated_details}"

    return {"messages": state["messages"] + [AIMessage(content=reply)]}
