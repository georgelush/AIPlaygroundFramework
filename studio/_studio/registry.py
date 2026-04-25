"""
_studio/registry.py - Standalone agent registry for the Studio addon.

Discovers agents by scanning the project's src/agents/ (or agents/) directory.
No dependency on src.registry or the src.agents package — works in any project.
"""
import importlib.util
import inspect
import os
import sys

# ── Registry dicts ─────────────────────────────────────────────────────────────
AGENTS: dict = {}
TRACES: dict = {}
META:   dict = {}

_project_root: str = ""
_agents_dir:   str = ""


# ── Public API ─────────────────────────────────────────────────────────────────

def load_agents(project_root: str) -> None:
    """Initial scan — call once at startup after sys.path is configured."""
    global _project_root, _agents_dir
    _project_root = project_root
    _agents_dir   = _find_agents_dir(project_root)

    AGENTS.clear()
    TRACES.clear()
    META.clear()

    if not _agents_dir:
        print("[Studio Registry] No src/agents/ or agents/ directory found.")
        return

    _scan(_agents_dir)
    print(f"[Studio Registry] Loaded {len(AGENTS)} agent(s): {', '.join(AGENTS.keys())}")


def reload_registry() -> None:
    """Re-scan agents directory and repopulate AGENTS, TRACES, META.
    Called by the reload button in the Studio UI.
    """
    AGENTS.clear()
    TRACES.clear()
    META.clear()

    if not _agents_dir:
        print("[Studio Registry] No agents directory configured.")
        return

    # Collect module names currently on disk
    files_on_disk: set[str] = set()
    for dirpath, dirnames, filenames in os.walk(_agents_dir):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for fname in filenames:
            if not fname.endswith(".py") or fname.startswith("_"):
                continue
            fpath = os.path.join(dirpath, fname)
            files_on_disk.add(_module_name(fpath))

    # Purge all agent modules from sys.modules so _scan always uses spec_from_file_location.
    # importlib.reload() requires the parent package to be in sys.modules — which is not
    # guaranteed here — so we always force a clean load via spec_from_file_location.
    rel_agents_prefix = os.path.relpath(_agents_dir, _project_root).replace(os.sep, ".") + "."
    for key in list(sys.modules.keys()):
        if key.startswith(rel_agents_prefix):
            del sys.modules[key]

    _scan(_agents_dir)
    print(f"[Studio Registry] Reloaded {len(AGENTS)} agent(s): {', '.join(AGENTS.keys())}")


# ── Internals ──────────────────────────────────────────────────────────────────

def _find_agents_dir(project_root: str) -> str:
    for candidate in [os.path.join("src", "agents"), "agents"]:
        path = os.path.join(project_root, candidate)
        if os.path.isdir(path):
            return path
    return ""


def _module_name(fpath: str) -> str:
    rel = os.path.relpath(fpath, _project_root)
    return rel.replace(os.sep, ".").removesuffix(".py")


def _find_framework_instance(mod):
    """Find an agent instance in a loaded module.

    Mirrors find_agent_instance() from spectrumai_agent_framework.cli.loader:

    Priority order:
    1. Pre-instantiated objects with ``invoke`` and ``name`` — prefers those
       with ``.app`` (LangGraph CompiledGraph) to avoid picking @tool functions.
    2. Agent classes defined in the module itself, tried via zero-arg init.
    """
    instances = []
    classes = []

    for attr_name in dir(mod):
        if attr_name.startswith("_"):
            continue
        obj = getattr(mod, attr_name, None)
        if obj is None:
            continue
        if not (callable(getattr(obj, "invoke", None)) and isinstance(getattr(obj, "name", None), str)):
            continue

        if inspect.isclass(obj):
            if getattr(obj, "__module__", None) == mod.__name__:
                classes.append((attr_name, obj))
        else:
            instances.append(obj)

    # Prefer compiled agent (has .app — present on ProductionAgent/ReactAgent)
    instances_with_app = [obj for obj in instances if hasattr(obj, "app")]
    if instances_with_app:
        return instances_with_app[0]

    if instances:
        return instances[0]

    # Fallback: zero-arg class instantiation
    for cls_name, cls in classes:
        try:
            return cls()
        except Exception:
            pass

    return None


def _make_run_fn(instance):
    """Wrap a framework agent instance into a Studio-compatible run_fn(payload)."""
    def run_fn(payload):
        message = payload.get("message", str(payload)) if isinstance(payload, dict) else str(payload)
        result = instance.invoke(message)
        if isinstance(result, dict):
            msgs = result.get("messages", [])
            return msgs[-1].content if msgs else ""
        return str(result) if result is not None else ""
    return run_fn


def _scan(agents_dir: str) -> None:
    for dirpath, dirnames, filenames in os.walk(agents_dir):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for fname in filenames:
            if not fname.endswith(".py") or fname.startswith("_"):
                continue

            fpath = os.path.join(dirpath, fname)
            mod_name = _module_name(fpath)

            try:
                if mod_name in sys.modules:
                    mod = importlib.reload(sys.modules[mod_name])
                else:
                    spec = importlib.util.spec_from_file_location(mod_name, fpath)
                    mod  = importlib.util.module_from_spec(spec)
                    sys.modules[mod_name] = mod
                    spec.loader.exec_module(mod)
            except Exception as exc:
                print(f"  [!] Could not load {mod_name}: {exc}")
                continue

            _llm   = getattr(mod, "llm", None) or getattr(mod, "llm_with_tools", None)
            _model = getattr(_llm, "model_name", None) or getattr(_llm, "model", None)

            # ── Convention 1: explicit run_agent (ping_agent backward compat) ──
            if hasattr(mod, "run_agent"):
                name = getattr(mod, "AGENT_NAME", fname.removesuffix(".py").replace("_", " ").title())
                AGENTS[name] = mod.run_agent
                TRACES[name] = getattr(mod, "trace_log", None)
                META[name] = {
                    "type":        getattr(mod, "AGENT_TYPE", "chat"),
                    "description": getattr(mod, "AGENT_DESCRIPTION", ""),
                    "module":      mod_name,
                    "model":       _model or "unknown",
                }
                continue

            # ── Convention 2: framework pattern (.invoke + .name on instance) ──
            instance = _find_framework_instance(mod)
            if instance is None:
                continue

            # display_name allows snake_case .name to show nicely (e.g. "HR Assistant")
            name = (
                getattr(instance, "display_name", None)
                or getattr(instance, "name", fname.removesuffix(".py")).replace("_", " ").title()
            )
            AGENTS[name] = _make_run_fn(instance)
            TRACES[name] = getattr(mod, "trace_log", None)
            META[name] = {
                "type":        "chat",
                "description": getattr(instance, "description", ""),
                "module":      mod_name,
                "model":       _model or "unknown",
            }
