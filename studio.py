"""
studio.py - Gradio debug UI for local agent development.
Usage: python studio.py
Visualize agents, execution trace, and test conversations in the browser.
"""
import gradio as gr
import inspect
from src.registry import AGENTS, TRACES, META, reload_registry
from src.config import LLM_MODEL


# ── CSS ─────────────────────────────────────────────────────────────────────────

CSS = """
/* ════════════════════════════════════════════════════════════
   Theme: Agentic Dark  (inspired by rusugeorge.com)
   bg        #06080f   very dark navy
   bg-panel  #090c16   panels
   bg-card   #0d1020   cards
   cyan      #00d4d4   tags / node_exec
   purple    #7c6fe0   main accent
   blue      #3b82f6   links / tool_call
   orange    #f97316   graph_call
   dim       #3a4060   borders
   text      #e2e8f0   main text
   text-dim  #64748b   secondary
   ════════════════════════════════════════════════════════════ */

/* ── RESET ───────────────────────────────────────────────── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body,
.gradio-container,
.gradio-container > .main,
.gradio-container > .main > .wrap,
.gradio-container .block,
.gradio-container .form,
.gradio-container .gap,
.gradio-container .panel,
.app {
    background: #0a0e18 !important;
    color: #e2e8f0 !important;
    font-family: 'Inter', 'Segoe UI', sans-serif !important;
}
html, body { overflow: hidden !important; margin: 0 !important; padding: 0 !important; }
footer { display: none !important; }
.gradio-container { max-width: 100% !important; padding: 14px 16px 20px 16px !important; }

/* ── RESPONSIVE HEIGHTS ────────────────────────────────────────────────────────
   --main-h  = height of the entire bordered box (chat + trace + input inside)
               100dvh - 32px container padding - 64px header - 10px gap
               - 48px dropdown - 10px gap = 100dvh - 164px
   --chat-h  = chatbot messages area only = --main-h - input(52px) - padding(28px)
   ─────────────────────────────────────────────────────────────────────────── */
:root {
    --main-h: calc(100dvh - 230px);
    --chat-h: calc(100dvh - 330px);
}

/* ── HEADER ──────────────────────────────────────────────── */
.app-header {
    background: linear-gradient(180deg, #0d1020 0%, #080c18 100%);
    border: 1px solid #1a2040;
    border-bottom: 1px solid #0d1028;
    box-shadow: 0 4px 24px rgba(0,0,0,0.5), 0 1px 0 rgba(255,255,255,0.03) inset;
    border-radius: 12px;
    padding: 8px 24px;
    margin-bottom: 10px;
    display: flex;
    align-items: center;
    gap: 14px;
}
.app-header-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(0,212,212,0.08);
    border: 1px solid rgba(0,212,212,0.25);
    border-radius: 20px;
    padding: 3px 12px;
    font-size: 0.7rem;
    color: #00d4d4;
    font-family: 'Courier New', monospace;
    letter-spacing: 0.05em;
    white-space: nowrap;
}
.app-header h2 {
    margin: 0;
    font-size: 1.25rem;
    font-weight: 800;
    letter-spacing: 0.02em;
    background: linear-gradient(135deg, #e2e8f0 30%, #7c6fe0 70%, #3b82f6 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

/* ── TOP BAR (label + select + reload button row) ── */
#top-bar-row,
#top-bar-row > div,
#top-bar-row > .wrap {
    background: linear-gradient(180deg, #0d1020 0%, #080c18 100%) !important;
    border: 1px solid #1a2040 !important;
    border-bottom: 1px solid #0d1028 !important;
    box-shadow: 0 4px 24px rgba(0,0,0,0.5), 0 1px 0 rgba(255,255,255,0.03) inset !important;
    border-radius: 12px !important;
    margin-bottom: 10px !important;
    padding: 10px 16px !important;
    align-items: center !important;
    gap: 0 !important;
}
#top-bar-html,
#top-bar-html > div,
#top-bar-html .block,
#top-bar-html .form {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 0 !important;
    flex: 1 !important;
}
/* Reload button — bright cyan/teal */
#reload-btn-id,
#reload-btn-id > div,
#reload-btn-id .block,
#reload-btn-id .form {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 0 !important;
    margin: 0 !important;
    flex-shrink: 0 !important;
}
#reload-btn-id button {
    background: linear-gradient(180deg, #5a4fd0 0%, #4035b0 100%) !important;
    border: 1px solid #6a5ee0 !important;
    border-bottom: 1px solid #2a2090 !important;
    border-radius: 8px !important;
    color: #e8e4ff !important;
    font-weight: 600 !important;
    font-size: 0.8rem !important;
    letter-spacing: 0.04em !important;
    height: 38px !important;
    padding: 0 22px !important;
    cursor: pointer !important;
    box-shadow: 0 4px 14px rgba(60,40,180,0.35), 0 1px 0 rgba(180,160,255,0.12) inset !important;
    white-space: nowrap !important;
    transition: all 0.15s ease !important;
}
#reload-btn-id button:hover {
    background: linear-gradient(180deg, #6a5fe0 0%, #5045c0 100%) !important;
    box-shadow: 0 6px 20px rgba(80,60,200,0.45), 0 1px 0 rgba(200,180,255,0.18) inset !important;
    transform: translateY(-1px) !important;
}
#reload-btn-id button:active {
    transform: translateY(1px) !important;
    box-shadow: 0 2px 6px rgba(60,40,160,0.3) !important;
}
/* Agent Dropdown — no box, no border anywhere */
.agent-dropdown,
.agent-dropdown *,
.agent-dropdown > .wrap,
.agent-dropdown > div,
.agent-dropdown .block,
.agent-dropdown .form,
#agent-dropdown,
#agent-dropdown *,
#agent-dropdown > .wrap,
#agent-dropdown > div,
#agent-dropdown .block,
#agent-dropdown .form {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    outline: none !important;
    padding: 0 !important;
    margin: 0 !important;
}
/* Re-apply style only to the actual input/select inside */
.agent-dropdown input,
#agent-dropdown input {
    background: linear-gradient(180deg, #0d1020 0%, #090c18 100%) !important;
    border: 1px solid #1e2545 !important;
    border-top: 1px solid #252d55 !important;
    border-radius: 8px !important;
    color: #c8d4f0 !important;
    font-size: 0.9rem !important;
    font-family: 'Inter', 'Segoe UI', sans-serif !important;
    height: 38px !important;
    min-height: 38px !important;
    padding: 0 12px !important;
    cursor: pointer !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.4) !important;
    outline: none !important;
}
#agent-dropdown input::placeholder { color: #4a5880 !important; }
#agent-dropdown svg { color: #4a5880 !important; fill: #4a5880 !important; }
#agent-dropdown ul,
#agent-dropdown [role="listbox"] {
    background: #0d1020 !important;
    border: 1px solid #1e2545 !important;
    border-radius: 8px !important;
    box-shadow: 0 8px 24px rgba(0,0,0,0.6) !important;
    padding: 4px !important;
}
#agent-dropdown li,
#agent-dropdown [role="option"] {
    color: #c8d4f0 !important;
    background: transparent !important;
    padding: 8px 12px !important;
    font-size: 0.9rem !important;
    cursor: pointer !important;
    border-radius: 6px !important;
}
#agent-dropdown li:hover,
#agent-dropdown [role="option"]:hover,
#agent-dropdown [aria-selected="true"] {
    background: rgba(124,111,224,0.15) !important;
    color: #e2e8f0 !important;
}

/* ── MAIN ROW (outer 3D box) ────────────────────────────── */
.main-row,
.main-row > .wrap,
.main-row > div {
    background: #090c16 !important;
    border: 1px solid #252d55 !important;
    border-top: 1px solid #2e3860 !important;
    border-radius: 14px !important;
    overflow: hidden !important;
    gap: 0 !important;
    height: var(--main-h) !important;
    max-height: var(--main-h) !important;
    box-shadow:
        0 0 0 1px rgba(255,255,255,0.04),
        0 2px 0 rgba(255,255,255,0.03) inset,
        0 -1px 0 rgba(0,0,0,0.6) inset,
        0 12px 50px rgba(0,0,0,0.8),
        0 4px 16px rgba(0,0,0,0.5) !important;
}

/* ── MAIN BOX (legacy, hide) ───────────────────────────────── */
.main-box,
.main-box > .wrap,
.main-box > div {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 0 !important;
    gap: 0 !important;
}

/* ── TRACE PANEL (inner 3D box) ─────────────────────────── */
.trace-panel,
.trace-panel > .wrap,
.trace-panel > div {
    background: #070a16 !important;
    border: none !important;
    border-right: 1px solid #1a2040 !important;
    box-shadow: 2px 0 8px rgba(0,0,0,0.4) inset !important;
    padding: 0 !important;
    margin: 0 !important;
    height: var(--main-h) !important;
    max-height: var(--main-h) !important;
    overflow: hidden !important;
}
.trace-panel label { display: none !important; }

.trace-panel-header {
    padding: 9px 14px;
    font-size: 0.65rem;
    font-weight: 700;
    color: #4a5880;
    border-bottom: 1px solid #1a2240;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    font-family: 'Courier New', monospace;
    background: linear-gradient(180deg, #111828 0%, #0c1020 100%);
    position: sticky;
    top: 0;
    box-shadow: 0 2px 10px rgba(0,0,0,0.4);
}
.trace-panel-inner {
    padding: 10px 8px;
    overflow-y: auto;
    height: calc(var(--main-h) - 35px);
}

/* ── CHAT COLUMN (inner box, right side) ──────────────────── */
.chat-col {
    background: #0b0e1c !important;
    border: none !important;
    padding: 10px 10px 10px 10px !important;
    height: var(--main-h) !important;
    max-height: var(--main-h) !important;
    display: flex !important;
    flex-direction: column !important;
    justify-content: center !important;
    overflow: hidden !important;
    gap: 0 !important;
}
.chat-col > .wrap {
    background: transparent !important;
    border: none !important;
    height: 100% !important;
    display: flex !important;
    flex-direction: column !important;
    justify-content: center !important;
    gap: 8px !important;
}
.chat-col > .wrap {
    background: #070910 !important;
    border: none !important;
    height: 100% !important;
    display: flex !important;
    flex-direction: column !important;
    justify-content: center !important;
    gap: 6px !important;
}

/* ── CHATBOT (inner message area with 3D inset) ─────────── */
.chatbot-box {
    flex: 0 0 auto !important;
    min-height: 0 !important;
    height: var(--chat-h) !important;
    max-height: var(--chat-h) !important;
    overflow-y: auto !important;
    background: #060910 !important;
    border: 1px solid #151c35 !important;
    border-top: 1px solid #1a2240 !important;
    border-radius: 10px !important;
    padding: 6px !important;
    box-shadow:
        0 2px 8px rgba(0,0,0,0.5) inset,
        0 1px 0 rgba(255,255,255,0.02) !important;
}
.chatbot-box > .wrap { background: transparent !important; border: none !important; height: 100% !important; }
.chatbot-box > div { background: transparent !important; border: none !important; }

.chatbot-box .bubble-wrap,
.chatbot-box .message-wrap,
.chatbot-box .message,
.chatbot-box [class*="message"],
.chatbot-box [class*="bubble"],
.chatbot-box [class*="bot"],
.chatbot-box [class*="user"] {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}

/* User messages */
.chatbot-box [data-testid="user"] {
    background: linear-gradient(135deg, #161e35 0%, #111828 100%) !important;
    border: 1px solid #1e2545 !important;
    border-left: 3px solid #3b82f6 !important;
    border-radius: 10px !important;
    padding: 10px 14px !important;
    margin: 5px 0 !important;
    box-shadow: 0 2px 12px rgba(0,0,0,0.35) !important;
    font-family: 'Inter', 'Segoe UI', sans-serif !important;
}
.chatbot-box [data-testid="user"] p,
.chatbot-box [data-testid="user"] span,
.chatbot-box [data-testid="user"] div {
    color: #94a3c8 !important;
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    font-size: 0.92rem !important;
}

/* Bot messages */
.chatbot-box [data-testid="bot"] {
    background: linear-gradient(145deg, #1a1640 0%, #151230 60%, #100e24 100%) !important;
    border: 1px solid #302860 !important;
    border-top: 1px solid #3c3478 !important;
    border-left: 3px solid #7c6fe0 !important;
    border-radius: 10px !important;
    padding: 12px 16px !important;
    margin: 5px 0 !important;
    box-shadow: 0 4px 20px rgba(60,40,160,0.2), 0 1px 0 rgba(140,120,255,0.05) inset !important;
    font-family: 'Inter', 'Segoe UI', sans-serif !important;
}
.chatbot-box [data-testid="bot"] p,
.chatbot-box [data-testid="bot"] span,
.chatbot-box [data-testid="bot"] div,
.chatbot-box [data-testid="bot"] li,
.chatbot-box [data-testid="bot"] ul,
.chatbot-box [data-testid="bot"] ol,
.chatbot-box [data-testid="bot"] h1,
.chatbot-box [data-testid="bot"] h2,
.chatbot-box [data-testid="bot"] h3 {
    color: #c8d0f0 !important;
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    line-height: 1.7 !important;
    font-size: 0.92rem !important;
}
.chatbot-box [data-testid="bot"] strong { color: #e2e8ff !important; }
.chatbot-box [data-testid="bot"] a { color: #7c6fe0 !important; }

.chatbot-box code {
    background: #0a081e !important;
    color: #c8c4ff !important;
    border: 1px solid #1e1a40 !important;
    border-radius: 4px !important;
    padding: 1px 6px !important;
    font-family: 'Courier New', Consolas, monospace !important;
    font-size: 0.83em !important;
}
.chatbot-box pre {
    background: #0a081e !important;
    border: 1px solid #1e1a40 !important;
    color: #e2e8f0 !important;
    border-radius: 8px !important;
    padding: 12px !important;
}
.chatbot-box .avatar-container { display: none !important; }

/* ── INPUT ───────────────────────────────────────────────── */
.input-wrap {
    flex-shrink: 0 !important;
    border-radius: 10px !important;
    padding: 1px !important;
    background: linear-gradient(135deg, #3b82f6, #7c6fe0) !important;
    margin-top: 8px !important;
    margin-bottom: 2px !important;
    box-shadow: 0 2px 14px rgba(124,111,224,0.2) !important;
    display: flex !important;
    flex-direction: row !important;
    align-items: center !important;
}
.input-wrap > div,
.input-wrap .block,
.input-wrap .form,
.input-wrap > .wrap {
    background: transparent !important;
    padding: 0 !important;
    border: none !important;
    box-shadow: none !important;
    gap: 4px !important;
    display: flex !important;
    flex-direction: row !important;
    align-items: center !important;
    width: 100% !important;
}
.input-wrap .gap { gap: 4px !important; }
.input-wrap textarea {
    background: #0b0e1e !important;
    color: #c8d4f0 !important;
    border: none !important;
    border-radius: 9px !important;
    caret-color: #7c6fe0 !important;
    min-height: 36px !important;
    max-height: 36px !important;
    padding: 8px 14px !important;
    font-size: 0.92rem !important;
    font-family: 'Inter', 'Segoe UI', sans-serif !important;
    resize: none !important;
}
.input-wrap textarea::placeholder { color: #2a3050 !important; }

/* ── SEND BUTTON ─────────────────────────────────────────── */
.send-btn,
.send-btn > div,
.send-btn > .wrap { background: transparent !important; border: none !important; padding: 0 !important; flex-shrink: 0 !important; }
.send-btn button {
    background: linear-gradient(180deg, #5a4fd0 0%, #4035b0 100%) !important;
    border-radius: 8px !important;
    border: 1px solid #6a5ee0 !important;
    border-bottom: 1px solid #2a2090 !important;
    color: #e8e4ff !important;
    font-weight: 600 !important;
    font-family: 'Inter', 'Segoe UI', sans-serif !important;
    letter-spacing: 0.04em !important;
    box-shadow: 0 4px 14px rgba(60,40,180,0.35), 0 1px 0 rgba(180,160,255,0.12) inset !important;
    height: 36px !important;
    min-height: 36px !important;
    max-height: 36px !important;
    width: 80px !important;
    min-width: 80px !important;
    max-width: 80px !important;
    font-size: 0.8rem !important;
    cursor: pointer !important;
    transition: all 0.15s ease !important;
    padding: 0 12px !important;
}
.send-btn button:hover {
    background: linear-gradient(180deg, #6a5fe0 0%, #5045c0 100%) !important;
    box-shadow: 0 6px 20px rgba(80,60,200,0.45), 0 1px 0 rgba(200,180,255,0.18) inset !important;
    transform: translateY(-1px) !important;
}
.send-btn button:active {
    transform: translateY(1px) !important;
    box-shadow: 0 2px 6px rgba(60,40,160,0.3) !important;
}

/* ── SCROLLBARS ──────────────────────────────────────────── */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #1e2545; border-radius: 2px; }
::-webkit-scrollbar-thumb:hover { background: #3a4898; }

/* ── RESPONSIVE — tablet (≤1024px) ───────────────────────── */
@media (max-width: 1024px) {
    :root {
        --main-h: calc(100dvh - 220px);
        --chat-h: calc(100dvh - 320px);
    }
}

/* ── RESPONSIVE — mobile (≤768px) ────────────────────────── */
@media (max-width: 768px) {
    body { overflow-y: auto; }
    :root {
        --main-h: 560px;
        --chat-h: 256px;
    }

    .main-row > div,
    .main-row > .wrap {
        flex-direction: column !important;
    }
    .trace-panel,
    .trace-panel > .wrap,
    .trace-panel > div {
        height: 280px !important;
        max-height: 280px !important;
        border-right: none !important;
        border-bottom: 1px solid #141830 !important;
    }
    .trace-panel-inner { height: 245px; }
    .chat-col {
        height: calc(100vh - 460px) !important;
        max-height: calc(100vh - 460px) !important;
        min-height: 320px !important;
    }
    .app-header { padding: 10px 14px; }
    .app-header h2 { font-size: 1rem !important; }
    .app-header-badge { display: none; }
}
"""

# ── Trace HTML builder ─────────────────────────────────────────────────────────

TYPE_COLORS = {
    "node_exec":    {"bg": "#0d2020", "border": "#1a4040", "label_color": "#00d4d4",  "arrow_color": "#00d4d4"},
    "tool_call":    {"bg": "#0d1c30", "border": "#1a3558", "label_color": "#3b82f6",  "arrow_color": "#3b82f6"},
    "tool_result":  {"bg": "#121228", "border": "#242458", "label_color": "#7c6fe0",  "arrow_color": "#7c6fe0"},
    "llm_response": {"bg": "#160e2e", "border": "#301e6a", "label_color": "#a78bfa",  "arrow_color": "#a78bfa"},
    "graph_call":   {"bg": "#1c1608", "border": "#4a2c10", "label_color": "#f97316",  "arrow_color": "#f97316"},
    "graph_result": {"bg": "#181408", "border": "#382808", "label_color": "#fbbf24",  "arrow_color": "#fbbf24"},
}


def build_trace_step(i: int, entry: dict) -> str:
    entry_type = entry.get("type", "")
    colors = TYPE_COLORS.get(entry_type, TYPE_COLORS["llm_response"])
    content = entry.get("content", "")[:100]
    label = entry.get("label", "")
    from_ = entry.get("from", "")
    to_ = entry.get("to", "")
    model = entry.get("model", "")
    temperature = entry.get("temperature", "")
    node = entry.get("fn", "")
    cost = entry.get("cost", "")

    if node:
        if entry_type in ("tool_call", "tool_result"):
            fn_prefix = "tool"
        elif entry_type in ("graph_call", "graph_result"):
            fn_prefix = "graph"
        else:
            fn_prefix = "node"
        node_badge = f"<span style='color:#404870; font-size:0.58rem; font-family:monospace; margin-right:3px;'>{fn_prefix} [{node}]</span>"
    else:
        node_badge = ""

    model_line = ""
    if model:
        temp_str = f" | temp = {temperature}" if (temperature is not None and temperature != "" and temperature != "n/a") else (" | temp = n/a" if temperature == "n/a" else "")
        model_line = f"<div style='font-size:0.62rem; color:#2a3860; font-family:monospace; margin-bottom:3px;'>model = <span style='color:#7c6fe0;'>{model}</span>{temp_str}</div>"

    arrow_color = colors["arrow_color"]
    label_color = colors["label_color"]
    border_color = colors["border"]
    bg_color = colors["bg"]

    is_graph = entry_type in ("graph_call", "graph_result")
    if is_graph:
        padding = "11px 13px"
        margin_bottom = "8px"
        border_left = f"3px solid {label_color}"
        from_style = f"color:{label_color}; font-weight:700; font-size:0.78rem;"
        to_style = f"color:{label_color}; font-weight:700; font-size:0.78rem;"
        arrow_html = f"<span style='color:{arrow_color}; font-size:1rem; font-weight:700; padding:0 4px;'>&#8594;</span>"
        content_color = "#a0b0c8"
    else:
        padding = "8px 10px"
        margin_bottom = "5px"
        border_left = f"2px solid {border_color}"
        from_style = "color:#8090c0; font-weight:600;"
        to_style = "color:#8090c0; font-weight:600;"
        arrow_html = f"<span style='color:{arrow_color}; font-size:0.9rem; opacity:0.8; white-space:nowrap;'>&#8594;</span>"
        content_color = "#7a8aaa"

    header_row = f"""
        <div style='display:flex; align-items:center; gap:6px; margin-bottom:4px; flex-wrap:nowrap;'>
            <span style='color:#1e2545; font-size:0.62rem; flex-shrink:0;'>#{i:02d}</span>
            <span style='{from_style} flex-shrink:0;'>{from_}</span>
            {arrow_html}
            <span style='{to_style} flex-shrink:0;'>{to_}</span>
        </div>
        <div style='display:flex; align-items:center; gap:4px; margin-bottom:4px; flex-wrap:wrap;'>
            {node_badge}<span style='border:1px solid {border_color};
                     color:{label_color}; border-radius:4px;
                     padding:1px 7px; font-size:0.6rem; letter-spacing:0.06em;
                     text-transform:uppercase; white-space:nowrap;'>{label}</span>
        </div>
        {f"<div style='margin-bottom:4px;'><span style='background:rgba(74,222,128,0.06); border:1px solid rgba(74,222,128,0.2); color:#4ade80; border-radius:4px; padding:2px 8px; font-size:0.62rem; font-family:monospace; white-space:nowrap;'>{cost}</span></div>" if cost else ""}"""

    return f"""
    <div style='background:{bg_color}; border:1px solid {border_color};
                border-left:{border_left};
                border-radius:8px; padding:{padding}; margin-bottom:{margin_bottom};
                font-family:"Courier New",Consolas,monospace; font-size:0.73rem;
                box-shadow:0 2px 8px rgba(0,0,0,0.3);'>
        {header_row}
        {model_line}
        <div style='color:{content_color}; font-size:0.68rem; word-break:break-all;
                    border-top:1px solid {border_color}; padding-top:4px; margin-top:2px;
                    line-height:1.4;'>
            {content if content else "<i style='color:#1a2040; font-style:italic;'>no content</i>"}
        </div>
    </div>"""


def build_agent_card(agent_name: str) -> str:
    agent_type = META.get(agent_name, {}).get("type", "chat")
    model = META.get(agent_name, {}).get("model", LLM_MODEL)
    return f"""
    <div style='background:linear-gradient(145deg,#1a1640,#151230,#100e24);
                border:1px solid #302860; border-top:1px solid #3c3478;
                border-left:3px solid #7c6fe0;
                border-radius:10px; padding:11px 14px; margin-bottom:10px;
                box-shadow:0 4px 20px rgba(60,40,160,0.2), 0 1px 0 rgba(140,120,255,0.05) inset;'>
        <div style='display:flex; justify-content:space-between; align-items:center;'>
            <span style='color:#c8d0f0; font-weight:700; font-size:0.85rem;'>{agent_name}</span>
            <span style='background:rgba(0,212,212,0.08); border:1px solid rgba(0,212,212,0.2);
                         border-radius:10px; padding:2px 8px;
                         color:#00d4d4; font-size:0.62rem; font-family:monospace; letter-spacing:0.06em;'>&#9679; {agent_type.upper()}</span>
        </div>
    </div>"""


def build_trace_html(agent_name: str) -> str:
    trace = TRACES.get(agent_name) or []
    agent_card = build_agent_card(agent_name)

    if not trace:
        body = "<div style='color:#333355; font-size:0.78rem; padding:6px; font-style:italic;'>Send a message to see the trace.</div>"
    else:
        steps = "".join(build_trace_step(i + 1, entry) for i, entry in enumerate(trace))
        body = f"""
        <div style='font-size:0.72rem; color:#404060; margin-bottom:6px; font-family:Consolas,monospace;'>
            &#8213; Execution trace ({len(trace)} steps)
        </div>
        {steps}"""

    return f"""
    <div class='trace-panel-header'>Trace Log</div>
    <div class='trace-panel-inner'>
        {agent_card}
        {body}
    </div>"""


# ── Chat logic ─────────────────────────────────────────────────────────────────

def chat(user_message: str, history: list, agent_name: str):
    if not user_message.strip():
        yield "", history, build_trace_html(agent_name)
        return

    run_fn = AGENTS[agent_name]
    result = run_fn(user_message)

    if inspect.isgenerator(result):
        partial = ""
        new_history = history + [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": ""},
        ]
        for token in result:
            partial += token
            new_history[-1]["content"] = partial
            yield "", new_history, build_trace_html(agent_name)
        yield "", new_history, build_trace_html(agent_name)
    else:
        if isinstance(result, dict):
            import json
            reply = f"```json\n{json.dumps(result, indent=2, ensure_ascii=False)}\n```"
        else:
            reply = result or ""
        new_history = history + [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": reply},
        ]
        yield "", new_history, build_trace_html(agent_name)


# ── UI Layout ──────────────────────────────────────────────────────────────────

def build_agent_bar():
    return """
<div id="agent-bar-inner">
    <span id="agent-bar-label">Agents</span>
</div>
<style>
#agent-bar-inner { display:flex; align-items:center; height:100%; }
#agent-bar-label {
    color: #6070a0;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    white-space: nowrap;
    font-family: 'Courier New', monospace;
}
</style>
"""

with gr.Blocks(title="Agent Studio") as demo:

    gr.HTML("""
    <div class='app-header'>
        <h2>Agentic AI Playground</h2>
    </div>
    """)

    # Top bar: ACTIVE AGENT label + Gradio Dropdown (native) + Reload button
    with gr.Row(elem_id="top-bar-row"):
        agent_bar_html = gr.HTML(value=build_agent_bar(), elem_id="top-bar-html", scale=0)
        agent_selector = gr.Dropdown(
            choices=list(AGENTS.keys()),
            value=list(AGENTS.keys())[0] if AGENTS else None,
            label="",
            show_label=False,
            elem_id="agent-dropdown",
            elem_classes=["agent-dropdown"],
            scale=6,
        )
        reload_btn = gr.Button("⟳ Reload", elem_id="reload-btn-id", scale=0, min_width=120, variant="primary", elem_classes=["reload-btn"])

    with gr.Row(elem_classes=["main-row"]):

            with gr.Column(scale=2, min_width=270, elem_classes=["trace-panel"]):
                debug_panel = gr.HTML(
                    value=build_trace_html(list(AGENTS.keys())[0]) if AGENTS else "",
                    label="",
                )

            with gr.Column(scale=5, elem_classes=["chat-col"]):
                chatbot = gr.Chatbot(
                    label="",
                    height=None,
                    show_label=False,
                    elem_classes=["chatbot-box"],
                )
                with gr.Row(elem_classes=["input-wrap"]):
                    user_input = gr.Textbox(
                        placeholder="Type your message...",
                        label="",
                        show_label=False,
                        scale=9,
                    )
                    send_btn = gr.Button("Send", scale=1, variant="primary", elem_classes=["send-btn"])

    def reload_agents():
        print("\n[Reload] ── Scanning src/agents/ ──────────────────────")
        reload_registry()
        choices = list(AGENTS.keys())
        value = choices[0] if choices else None
        print(f"[Reload] Found {len(choices)} agent(s): {', '.join(choices) if choices else 'none'}")
        print("[Reload] ── Done ─────────────────────────────\n")
        return gr.Dropdown(choices=choices, value=value)

    reload_btn.click(
        fn=reload_agents,
        inputs=[],
        outputs=[agent_selector],
    )

    send_btn.click(
        fn=chat,
        inputs=[user_input, chatbot, agent_selector],
        outputs=[user_input, chatbot, debug_panel],
    )
    user_input.submit(
        fn=chat,
        inputs=[user_input, chatbot, agent_selector],
        outputs=[user_input, chatbot, debug_panel],
    )

if __name__ == "__main__":
    print(f"[Studio] Ready at http://127.0.0.1:8000")
    demo.launch(server_port=8000, inbrowser=True, css=CSS, theme=gr.themes.Base())
