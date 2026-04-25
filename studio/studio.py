"""
Studio/studio.py - Entry point for the Studio addon.

Drop the Studio/ folder into any project and run:
    python Studio/studio.py

Requirements:
    pip install -r Studio/requirements.txt
    (or: .\\Studio\\studio-setup.ps1  on Windows)
    (or: bash Studio/studio-setup.sh  on Linux/Mac)
"""
import sys
import os

# ── Resolve paths ──────────────────────────────────────────────────────────────
_this_dir    = os.path.dirname(os.path.abspath(__file__))   # .../Studio/
_project_root = os.path.dirname(_this_dir)                  # parent project root

# Add project root to sys.path so agents can do: from src.config import ...
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# Add Studio/ dir to sys.path so _studio package is importable
if _this_dir not in sys.path:
    sys.path.insert(0, _this_dir)

# ── Load .env from project root ────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    _env_file = os.path.join(_project_root, ".env")
    if os.path.exists(_env_file):
        load_dotenv(_env_file)
        print("[Studio] Loaded .env")
    else:
        print(f"[Studio] No .env found at {_env_file} — skipping")
except ImportError:
    print("[Studio] python-dotenv not installed — .env not loaded")

# ── Load agents from project's src/agents/ (or agents/) ───────────────────────
from _studio.registry import load_agents
load_agents(_project_root)

# ── Launch Gradio UI ───────────────────────────────────────────────────────────
from _studio.ui import build_and_launch

if __name__ == "__main__":
    build_and_launch(port=8000)
