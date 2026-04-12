"""
src/registry.py - Auto-discovers and registers all agents from src/agents/.
Shared between studio.py (debug UI) and server.py (FastAPI).

A file is registered if it defines run_agent().
Optional metadata per agent file:
    AGENT_NAME = "My Agent"          # display name (fallback: filename)
    AGENT_TYPE = "chat"              # "chat" | "processor" | "pipeline" | ...
    AGENT_DESCRIPTION = "Does X"    # shown in /agents endpoint
    trace_log: list[dict] = []      # if present, trace is captured
"""
import importlib
import os
import src.agents as _agents_pkg

# ── Registry dicts ─────────────────────────────────────────────────────────────
AGENTS: dict = {}   # name -> run_agent callable
TRACES: dict = {}   # name -> trace_log list (or None)
META:   dict = {}   # name -> {type, description, module}

_agents_root    = os.path.dirname(_agents_pkg.__file__)
_agents_pkg_name = _agents_pkg.__name__  # "src.agents"

for _dirpath, _dirnames, _filenames in os.walk(_agents_root):
    _dirnames[:] = [d for d in _dirnames if d != "__pycache__"]
    for _fname in _filenames:
        if not _fname.endswith(".py") or _fname.startswith("_"):
            continue
        _rel = os.path.relpath(os.path.join(_dirpath, _fname), _agents_root)
        _module_path = f"{_agents_pkg_name}.{_rel.replace(os.sep, '.').removesuffix('.py')}"
        try:
            _mod = importlib.import_module(_module_path)
        except Exception as e:
            print(f"  [!] Could not load {_module_path}: {e}")
            continue
        if not hasattr(_mod, "run_agent"):
            continue
        _name = getattr(_mod, "AGENT_NAME", _fname.removesuffix(".py").replace("_", " ").title())
        AGENTS[_name] = _mod.run_agent
        TRACES[_name] = getattr(_mod, "trace_log", None)
        _llm = getattr(_mod, "llm", None) or getattr(_mod, "llm_with_tools", None)
        _model = getattr(_llm, "model_name", None) or getattr(_llm, "model", None)
        META[_name] = {
            "type":        getattr(_mod, "AGENT_TYPE", "chat"),
            "description": getattr(_mod, "AGENT_DESCRIPTION", ""),
            "module":      _module_path,
            "model":       _model or "unknown",
        }

print(f"[Registry] Loaded {len(AGENTS)} agent(s): {', '.join(AGENTS.keys())}")


def reload_registry():
    """Re-scan src/agents/ and repopulate AGENTS, TRACES, META.
    Call this when a new agent file is added or removed without restarting Studio.
    Purges deleted modules from sys.modules so removed agents disappear correctly.
    """
    import sys

    AGENTS.clear()
    TRACES.clear()
    META.clear()

    # Collect all files currently on disk
    _files_on_disk = set()
    for _dirpath, _dirnames, _filenames in os.walk(_agents_root):
        _dirnames[:] = [d for d in _dirnames if d != "__pycache__"]
        for _fname in _filenames:
            if not _fname.endswith(".py") or _fname.startswith("_"):
                continue
            _rel = os.path.relpath(os.path.join(_dirpath, _fname), _agents_root)
            _module_path = f"{_agents_pkg_name}.{_rel.replace(os.sep, '.').removesuffix('.py')}"
            _files_on_disk.add(_module_path)

    # Remove from sys.modules any agent module that no longer exists on disk
    for _key in list(sys.modules.keys()):
        if _key.startswith(_agents_pkg_name + ".") and _key not in _files_on_disk:
            del sys.modules[_key]

    # Now reload/import modules that exist on disk
    for _module_path in _files_on_disk:
        _fname = _module_path.split(".")[-1] + ".py"
        try:
            if _module_path in sys.modules:
                _mod = importlib.reload(sys.modules[_module_path])
            else:
                _mod = importlib.import_module(_module_path)
        except Exception as e:
            print(f"  [!] Could not load {_module_path}: {e}")
            continue
        if not hasattr(_mod, "run_agent"):
            continue
        _name = getattr(_mod, "AGENT_NAME", _fname.removesuffix(".py").replace("_", " ").title())
        AGENTS[_name] = _mod.run_agent
        TRACES[_name] = getattr(_mod, "trace_log", None)
        _llm = getattr(_mod, "llm", None) or getattr(_mod, "llm_with_tools", None)
        _model = getattr(_llm, "model_name", None) or getattr(_llm, "model", None)
        META[_name] = {
            "type":        getattr(_mod, "AGENT_TYPE", "chat"),
            "description": getattr(_mod, "AGENT_DESCRIPTION", ""),
            "module":      _module_path,
            "model":       _model or "unknown",
        }
    print(f"[Registry] Reloaded {len(AGENTS)} agent(s): {', '.join(AGENTS.keys())}")
