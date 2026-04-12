"""
Lab 20 — Capstone Agent: HR Assistant

Demonstrates production-ready agent architecture — the correct separation of concerns:
- src/tools/hr_tools.py  → search_hr_handbook (RAG via Qdrant) + calculate_leave_days + submit_vacation_request
- src/nodes/hr_nodes.py  → node_llm + node_approve (HITL) + LLM instantiation + _node_trace buffer
- src/graphs/hr_graph.py → StateGraph compiled once with Redis checkpointer (HITL persistence)
- src/agents/capstone_agent.py → entry point only — RBAC + budget + request-ID routing

Data: src/data/hr_handbook.txt — indexed into Qdrant in-memory on first call.
Infrastructure: docker compose up -d redis
Agent type: chat | multilingual | RAG | HITL vacation approval
"""
import re
from datetime import datetime, timezone
from langchain_core.messages import HumanMessage
from langgraph.types import Command
import redis

from src.config import REDIS_URL
from src.graphs.hr_graph import graph
from src.nodes.hr_nodes import (
    _node_trace as _hr_node_trace,
    _cost_tracker,
    validate_input,
    detect_injection,
    sanitize_output,
    resolve_pending_request,
    tag_pending_request_employee,
)

AGENT_NAME = "HR Assistant"
AGENT_TYPE = "chat"
AGENT_DESCRIPTION = "Answers HR questions via RAG on the company handbook. Supports vacation request submission with HR approval gate (HITL). Multilingual. Demonstrates src/tools/ + src/nodes/ + src/graphs/ separation."

trace_log: list[dict] = []

# ── RBAC ────────────────────────────────────────────────────────────────────────────
ROLE_PERMISSIONS: dict[str, list[str]] = {
    "guest":    ["ask_hr"],
    "employee": ["ask_hr", "calculate_days", "submit_vacation"],
    "manager":  ["ask_hr", "calculate_days", "submit_vacation", "approve_vacation"],
    "admin":    ["ask_hr", "calculate_days", "submit_vacation", "approve_vacation", "ask_admin"],
}

# Identity store — replace with Active Directory / OAuth2 in production
_user_roles: dict[str, str] = {
    "alice":    "manager",
    "bob":      "employee",
    "carol":    "guest",
    "hr_admin": "admin",
}

audit_log: list[dict] = []  # separate audit trail — never cleared between requests

# ── Token budget (Lab 13 + 15 pattern) — Redis with 24h TTL ──────────────────
# Each user_id gets USER_TOKEN_BUDGET tokens per 24-hour window.
# Budget is stored in Redis — survives restarts, shared across all instances.
USER_TOKEN_BUDGET = 40_000  # tokens per 24h window
BUDGET_TTL = 86_400          # 24 hours in seconds

_redis = redis.from_url(REDIS_URL, decode_responses=True)

# Pattern for cross-thread approval: 'approve:REQ-A1B2C3D4' or 'reject:REQ-A1B2C3D4'
_APPROVE_PATTERN = re.compile(r"^(approve|reject):(REQ-[A-F0-9]{8})$", re.IGNORECASE)

# Pattern for admin budget reset: 'reset budget bob' or 'reset budget all'
_RESET_PATTERN = re.compile(r"^reset\s+budget\s+(\S+)$", re.IGNORECASE)


def _budget_key(user_id: str) -> str:
    return f"hr:budget:{user_id}"


def _get_tokens_used(user_id: str) -> int:
    """Returns tokens used by user_id in the current 24h window."""
    val = _redis.get(_budget_key(user_id))
    return int(val) if val else 0


def _record_tokens(user_id: str, tokens: int) -> None:
    """Adds tokens to the user's 24h budget counter. Sets TTL on first write."""
    key = _budget_key(user_id)
    pipe = _redis.pipeline()
    pipe.incrby(key, tokens)
    pipe.expire(key, BUDGET_TTL)  # reset TTL window on every call
    pipe.execute()


def get_role(user_id: str) -> str:
    """Returns the role for a user_id. Defaults to 'employee' if unknown."""
    return _user_roles.get(user_id.lower(), "employee")


def has_permission(role: str, action: str) -> bool:
    """Returns True if the given role is allowed to perform the action."""
    return action in ROLE_PERMISSIONS.get(role, [])


def _detect_action(message: str) -> str:
    """Infers the intended action from the message content for RBAC enforcement."""
    lower = message.strip().lower()
    if re.match(r"^(approve|reject)\b", lower):
        return "approve_vacation"
    if re.search(r"\b(submit|request|book).{0,20}vacation|vacation.{0,20}(request|days off)", lower):
        return "submit_vacation"
    if re.search(r"\b(how many (working )?days|calculate|count days)\b", lower):
        return "calculate_days"
    return "ask_hr"


def record_audit(user_id: str, role: str, action: str, outcome: str) -> None:
    """Appends an immutable audit entry with UTC timestamp."""
    audit_log.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "user_id":   user_id,
        "role":      role,
        "action":    action,
        "outcome":   outcome,
    })


def run_agent(payload) -> str:
    trace_log.clear()
    _hr_node_trace.clear()
    # Reset cost tracker at the start of every run
    _cost_tracker.__init__()

    if isinstance(payload, dict):
        user_input = payload.get("message", "")
        thread_id = payload.get("thread_id", "default")
        user_id = payload.get("user_id", "anonymous")
    else:
        user_input = str(payload) if payload else ""
        thread_id = "default"
        user_id = "anonymous"

    # Parse @user_id prefix from message (compatible with Lab 16 Studio pattern)
    # Example: "@alice I want to request vacation from 2026-07-01"
    if user_input.startswith("@"):
        parts = user_input.split(" ", 1)
        user_id = parts[0][1:]  # strip leading "@"
        user_input = parts[1] if len(parts) > 1 else ""

    role = get_role(user_id)
    config = {"configurable": {"thread_id": thread_id}}

    # ── Security validation at system boundary (Lab 14 pattern) ─────────────────────────
    validation_error = validate_input(user_input)
    if validation_error:
        record_audit(user_id, role, "unknown", "blocked:invalid_input")
        return validation_error

    if detect_injection(user_input):
        record_audit(user_id, role, "unknown", "blocked:injection")
        trace_log.append({
            "type": "node_exec",
            "label": "Security Reject",
            "from": "validator",
            "to": "user",
            "arrow": "->",
            "content": "Prompt injection detected — request blocked",
        })
        return "Request blocked: potential prompt injection detected."

    # ── RBAC check (Lab 16 pattern) ───────────────────────────────────────────────
    # HITL resumes (approve/reject) require manager role.
    action = _detect_action(user_input)
    if not has_permission(role, action):
        record_audit(user_id, role, action, "denied")
        trace_log.append({
            "type": "node_exec",
            "label": "Auth Denied",
            "from": "auth",
            "to": "user",
            "arrow": "->",
            "content": f"user={user_id} | role={role} | action={action} → DENIED",
        })
        return f"Access denied. Role '{role}' cannot perform '{action}'. Contact your manager."

    record_audit(user_id, role, action, "allowed")
    trace_log.append({
        "type": "node_exec",
        "label": f"Auth OK [{role}]",
        "from": "auth",
        "to": "graph",
        "arrow": "->",
        "content": f"user={user_id} | role={role} | action={action} | allowed",
    })

    # ── Admin: reset token budget ─────────────────────────────────────────────
    # Only admins can do this. Format: 'reset budget bob' or 'reset budget all'
    rm = _RESET_PATTERN.match(user_input.strip())
    if rm:
        if role != "admin":
            record_audit(user_id, role, "ask_admin", "denied")
            return "Access denied. Only admins can reset budgets."
        target = rm.group(1).lower()
        if target == "all":
            keys = _redis.keys("hr:budget:*")
            if keys:
                _redis.delete(*keys)
            deleted = len(keys)
            record_audit(user_id, role, "reset_budget", f"all ({deleted} users)")
            trace_log.append({
                "type": "node_exec",
                "label": "Budget Reset [ALL]",
                "from": "admin",
                "to": "redis",
                "arrow": "->",
                "content": f"admin={user_id} | reset all budgets | {deleted} keys deleted",
            })
            return f"Budget reset for all users ({deleted} users cleared)."
        else:
            key = _budget_key(target)
            existed = _redis.exists(key)
            _redis.delete(key)
            record_audit(user_id, role, "reset_budget", f"user={target}")
            trace_log.append({
                "type": "node_exec",
                "label": f"Budget Reset [{target}]",
                "from": "admin",
                "to": "redis",
                "arrow": "->",
                "content": f"admin={user_id} | reset budget for {target} | existed={bool(existed)}",
            })
            return f"Budget reset for '{target}'." if existed else f"No active budget found for '{target}' (may have already expired)."

    # ── Admin: reset pending vacation requests ────────────────────────────────
    # Format: 'reset requests' — deletes all hr:pending:* keys from Redis
    if user_input.strip().lower() == "reset requests":
        if role != "admin":
            record_audit(user_id, role, "ask_admin", "denied")
            return "Access denied. Only admins can reset requests."
        keys = _redis.keys("hr:pending:*")
        if keys:
            _redis.delete(*keys)
        deleted = len(keys)
        record_audit(user_id, role, "reset_requests", f"all ({deleted} requests)")
        trace_log.append({
            "type": "node_exec",
            "label": "Requests Reset [ALL]",
            "from": "admin",
            "to": "redis",
            "arrow": "->",
            "content": f"admin={user_id} | deleted {deleted} pending request(s)",
        })
        return f"All pending requests cleared ({deleted} deleted)." if deleted else "No pending requests found in Redis."

    # ── Cross-thread HITL approval by REQUEST_ID ─────────────────────────────────
    # Manager types 'approve:REQ-XXXXXXXX' or 'reject:REQ-XXXXXXXX' from any tab.
    # We look up the original thread_id from Redis and resume the paused graph there.
    m = _APPROVE_PATTERN.match(user_input.strip())
    if m:
        decision = m.group(1).lower()      # "approve" or "reject"
        request_id = m.group(2).upper()    # "REQ-XXXXXXXX"
        req_data = resolve_pending_request(request_id)
        if not req_data:
            return f"Request '{request_id}' not found or already processed."
        if req_data.get("status") != "pending":
            return f"Request '{request_id}' has already been {req_data.get('status', 'processed')}."
        # Self-approval check — a user cannot approve their own vacation request
        employee_id = req_data.get("employee_id")
        if employee_id and employee_id.lower() == user_id.lower():
            record_audit(user_id, role, "approve_vacation", "denied:self-approval")
            trace_log.append({
                "type": "node_exec",
                "label": f"Self-Approval Denied [{user_id}]",
                "from": "auth",
                "to": "user",
                "arrow": "->",
                "content": f"user={user_id} tried to approve their own request {request_id}",
            })
            return f"Access denied. You cannot approve your own vacation request ({request_id})."
        original_config = {"configurable": {"thread_id": req_data["thread_id"]}}
        paused_state = graph.get_state(original_config)
        if not paused_state.next:
            return f"Request '{request_id}' is no longer waiting for approval (graph not paused)."
        trace_log.append({
            "type": "graph_call",
            "label": f"Resume [{request_id}]",
            "from": "agent",
            "to": "graph",
            "arrow": "->",
            "content": f"decision={decision} | thread={req_data['thread_id']}",
        })
        result = graph.invoke(Command(resume=f"{decision}:{user_id}"), config=original_config)
        response = result["messages"][-1].content or ""
        response = sanitize_output(response)
        cost_summary = _cost_tracker.get_cost_summary()
        trace_log.extend(_hr_node_trace)
        trace_log.append({
            "type": "graph_result",
            "label": "HR Graph",
            "from": "graph",
            "to": "agent",
            "arrow": "<-",
            "content": response[:200],
        })
        trace_log.append({
            "type": "llm_response",
            "label": "HR Assistant",
            "from": "agent",
            "to": "user",
            "arrow": "->",
            "content": response[:200],
        })
        return response

    # ── Token budget check (Lab 13 + 15 pattern) — Redis TTL window ─────────────────────────────────────
    tokens_used = _get_tokens_used(user_id)
    if tokens_used >= USER_TOKEN_BUDGET:
        record_audit(user_id, role, action, "blocked:budget")
        trace_log.append({
            "type": "node_exec",
            "label": f"Budget Exceeded [{user_id}]",
            "from": "budget",
            "to": "user",
            "arrow": "->",
            "content": f"user={user_id} | used={tokens_used}/{USER_TOKEN_BUDGET} tokens | window=24h",
        })
        return f"Token budget exceeded for '{user_id}' ({tokens_used}/{USER_TOKEN_BUDGET} tokens used in the last 24h). Contact HR admin to reset."

    trace_log.append({
        "type": "graph_call",
        "label": "HR Graph",
        "from": "agent",
        "to": "graph",
        "arrow": "->",
        "content": user_input[:200],
    })

    # Check if graph is paused at an interrupt on the current thread
    state = graph.get_state(config)
    if state.next:
        result = graph.invoke(Command(resume=user_input.strip()), config=config)
    else:
        result = graph.invoke({"messages": [HumanMessage(content=user_input)]}, config=config)

    # Check if graph paused again after this invoke (new interrupt)
    state_after = graph.get_state(config)
    if state_after.next:
        # Extract REQUEST_ID from _hr_node_trace — node_approve writes it before interrupt()
        req_id = None
        for entry in _hr_node_trace:
            if entry.get("label", "").startswith("HITL Pending ["):
                req_id = entry["label"][len("HITL Pending ["):-1]
                break
        if req_id:
            # Tag the Redis record with the employee who submitted — used for self-approval check
            tag_pending_request_employee(req_id, user_id)
            response = (
                f"Vacation request submitted — pending manager approval.\n\n"
                f"**Request ID:** `{req_id}`\n\n"
                f"Manager — copy one of these into the chat to process:\n\n"
                f"```\napprove:{req_id}\n```\n\n"
                f"```\nreject:{req_id}\n```"
            )
        else:
            # Last resort: try LangGraph tasks API
            try:
                response = str(state_after.tasks[0].interrupts[0].value)
            except (IndexError, AttributeError):
                response = "Your vacation request is pending HR approval."
    else:
        response = result["messages"][-1].content or ""

    # Output sanitization (Lab 14 pattern) — strips accidental system prompt leakage
    response = sanitize_output(response)

    # ── Record actual token usage against user budget ─────────────────────────────
    cost_summary = _cost_tracker.get_cost_summary()
    tokens_this_run = cost_summary["total_input_tokens"] + cost_summary["total_output_tokens"]
    if tokens_this_run > 0:
        _record_tokens(user_id, tokens_this_run)
        tokens_now = _get_tokens_used(user_id)
        trace_log.append({
            "type": "node_exec",
            "label": f"Budget [{user_id}] {tokens_now}/{USER_TOKEN_BUDGET}",
            "from": "budget",
            "to": "agent",
            "arrow": "->",
            "content": f"used={tokens_now} | budget={USER_TOKEN_BUDGET} | this_run={tokens_this_run} | window=24h TTL",
        })

    # Merge tool_call / tool_result / node_exec / llm_response (with cost) entries from inside the graph
    trace_log.extend(_hr_node_trace)

    # Append cost summary from this run
    trace_log.append({
        "type": "node_exec",
        "label": f"cost total=${cost_summary['total_cost_usd']}",
        "from": "tracker",
        "to": "agent",
        "arrow": "->",
        "content": (
            f"total_input_tokens={cost_summary['total_input_tokens']} | "
            f"total_output_tokens={cost_summary['total_output_tokens']} | "
            f"total_cost_usd=${cost_summary['total_cost_usd']}"
        ),
    })

    trace_log.append({
        "type": "graph_result",
        "label": "HR Graph",
        "from": "graph",
        "to": "agent",
        "arrow": "<-",
        "content": response[:200],
    })

    trace_log.append({
        "type": "llm_response",
        "label": "HR Assistant",
        "from": "agent",
        "to": "user",
        "arrow": "->",
        "content": response[:200],
    })

    return response

