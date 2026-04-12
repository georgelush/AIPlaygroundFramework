"""
Lab 18 — Test Agent

Demonstrates automated testing patterns for LangGraph agents:
- Mock LLM: replace the real LLM with a fake one — no API cost, fully deterministic
- Trace assertions: verify the agent followed the correct execution path
- Contract checks: verify every agent exposes AGENT_NAME, AGENT_TYPE, run_agent
- Regression suite: run all checks at once — any failure is reported immediately

This agent IS itself a test runner — send "run tests" in Studio and it executes
a suite of checks against the other agents in src/agents/, then reports results.

Pattern: processor — takes a command, returns a structured report.
New concepts: unittest.mock, MagicMock, patch, assert statements, test report.
"""

import importlib
import pkgutil
from unittest.mock import MagicMock, patch

import src.agents as agents_pkg
from src.config import LLM_MODEL, LLM_PROXY, LLM_API_KEY, langfuse_handler
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

AGENT_NAME = "Test Agent"
AGENT_TYPE = "processor"
AGENT_DESCRIPTION = "Runs automated checks against all agents in src/agents/ — contract validation, mock LLM tests, trace assertions."

trace_log: list[dict] = []

def _discover_agents() -> list:
    """Return list of (module_name, module) for every agent in src/agents/."""
    agents = []
    for finder, module_name, _ in pkgutil.iter_modules(agents_pkg.__path__):
        full_name = f"src.agents.{module_name}"
        try:
            mod = importlib.import_module(full_name)
            agents.append((module_name, mod))
        except Exception as e:
            agents.append((module_name, None))
    return agents

def _check_contract(module_name: str, mod) -> dict:
    """Verify a module exposes the required agent contract fields."""
    result = {"test": "contract", "agent": module_name, "passed": True, "errors": []}

    for attr in ("AGENT_NAME", "AGENT_TYPE", "AGENT_DESCRIPTION", "trace_log", "run_agent"):
        if not hasattr(mod, attr):
            result["passed"] = False
            result["errors"].append(f"missing: {attr}")

    if result["passed"]:
        if not callable(getattr(mod, "run_agent")):
            result["passed"] = False
            result["errors"].append("run_agent is not callable")

    return result

def _check_trace_log(module_name: str, mod) -> dict:
    """Verify trace_log is populated after run_agent() is called."""
    result = {"test": "trace_log", "agent": module_name, "passed": True, "errors": []}

    try:
        mod.trace_log.clear()
        mod.run_agent("test input")

        if len(mod.trace_log) == 0:
            result["passed"] = False
            result["errors"].append("trace_log is empty after run_agent()")

        for entry in mod.trace_log:
            for key in ("type", "label", "content"):
                if key not in entry:
                    result["passed"] = False
                    result["errors"].append(f"trace entry missing key: {key}")
                    break

    except Exception as e:
        result["passed"] = False
        result["errors"].append(f"run_agent() raised: {str(e)[:100]}")

    return result

def _check_mock_llm(module_name: str, mod) -> dict:
    """Verify the agent can run when the LLM is replaced with a MagicMock."""
    result = {"test": "mock_llm", "agent": module_name, "passed": True, "errors": []}

    mock_response = MagicMock()
    mock_response.content = "mocked response"

    mock_llm = MagicMock()
    mock_llm.invoke.return_value = mock_response
    mock_llm.bind_tools.return_value = mock_llm

    try:
        with patch("langchain_openai.ChatOpenAI", return_value=mock_llm):
            mod.trace_log.clear()
            output = mod.run_agent("test input")

        if output is None:
            result["passed"] = False
            result["errors"].append("run_agent() returned None with mock LLM")

    except Exception as e:
        result["passed"] = False
        result["errors"].append(f"mock run raised: {str(e)[:100]}")

    return result

def _run_all_checks() -> dict:
    """Discover all agents and run every check against each one."""
    agents = _discover_agents()
    results = []
    passed = 0
    failed = 0

    for module_name, mod in agents:
        if mod is None:
            results.append({"agent": module_name, "test": "import", "passed": False, "errors": ["failed to import"]})
            failed += 1
            continue

        for check_fn in (_check_contract, _check_trace_log, _check_mock_llm):
            r = check_fn(module_name, mod)
            results.append(r)
            if r["passed"]:
                passed += 1
            else:
                failed += 1

    return {"total": passed + failed, "passed": passed, "failed": failed, "results": results}

def run_agent(payload) -> str:
    trace_log.clear()

    if isinstance(payload, str):
        command = payload.strip().lower()
    else:
        command = str(payload).strip().lower()

    if command != "run tests":
        trace_log.append({
            "type": "llm_response",
            "label": "Test Agent",
            "from": "user",
            "to": "agent",
            "arrow": "->",
            "content": "Send 'run tests' to execute the full test suite.",
        })
        return "Send 'run tests' to execute the full test suite."

    trace_log.append({
        "type": "node_exec",
        "label": "run_all_checks",
        "from": "agent",
        "to": "suite",
        "arrow": "->",
        "content": "Starting test suite across all agents in src/agents/",
    })

    report = _run_all_checks()

    # Group results by agent
    by_agent: dict[str, list] = {}
    for r in report["results"]:
        by_agent.setdefault(r["agent"], []).append(r)

    lines = [f"TEST SUITE RESULTS — {report['passed']}/{report['total']} passed\n"]

    for agent_name, checks in by_agent.items():
        agent_pass = sum(1 for c in checks if c["passed"])
        agent_fail = sum(1 for c in checks if not c["passed"])

        lines.append("═" * 44)
        lines.append(f"  {agent_name}")
        lines.append("═" * 44)

        for c in checks:
            if c["passed"]:
                lines.append(f"  {c['test']:<15} = ok")
            else:
                for err in c["errors"]:
                    lines.append(f"  {c['test']:<15} = FAIL  ({err})")

        lines.append("─" * 44)
        if agent_fail == 0:
            lines.append(f"  {agent_pass} passed / 0 failed")
        else:
            lines.append(f"  {agent_pass} passed / {agent_fail} failed")
        lines.append("")

    lines.append("═" * 44)
    lines.append(f"  TOTAL  passed={report['passed']}  failed={report['failed']}")
    lines.append("═" * 44)

    output = "```\n" + "\n".join(lines) + "\n```"

    trace_log.append({
        "type": "llm_response",
        "label": "Report",
        "from": "suite",
        "to": "user",
        "arrow": "->",
        "content": f"total={report['total']} passed={report['passed']} failed={report['failed']}",
    })

    return output
