"""
studio.py - Gradio debug UI for local agent development.
Usage: python studio.py
Visualize agents, execution trace, and test conversations in the browser.
"""
import gradio as gr
from src.registry import AGENTS, TRACES, META


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
    background: #06080f !important;
    color: #e2e8f0 !important;
    font-family: 'Inter', 'Segoe UI', sans-serif !important;
}
body { overflow: hidden; }
footer { display: none !important; }
.gradio-container { max-width: 100% !important; padding: 10px !important; }

/* ── HEADER ──────────────────────────────────────────────── */
.app-header {
    background: linear-gradient(180deg, #0d1020 0%, #080c18 100%);
    border: 1px solid #1a2040;
    border-bottom: 1px solid #0d1028;
    box-shadow: 0 4px 24px rgba(0,0,0,0.5), 0 1px 0 rgba(255,255,255,0.03) inset;
    border-radius: 12px;
    padding: 14px 24px;
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

/* ── DROPDOWN ────────────────────────────────────────────── */
.agent-dropdown { margin-bottom: 10px; }
.agent-dropdown label {
    color: #00d4d4 !important;
    font-size: 0.7rem !important;
    font-family: 'Courier New', monospace !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
}
.agent-dropdown input,
.agent-dropdown .wrap-inner,
.agent-dropdown .wrap,
.agent-dropdown .secondary-wrap {
    background: linear-gradient(180deg, #0d1020 0%, #090c18 100%) !important;
    color: #c8d4f0 !important;
    border: 1px solid #1e2545 !important;
    border-top: 1px solid #252d55 !important;
    border-radius: 8px !important;
    font-size: 0.9rem !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.4) !important;
}

/* ── MAIN ROW ────────────────────────────────────────────── */
.main-row,
.main-row > .wrap,
.main-row > div {
    background: #090c16 !important;
    border: 1px solid #1a2040 !important;
    border-radius: 14px !important;
    overflow: hidden !important;
    gap: 0 !important;
    box-shadow: 0 8px 40px rgba(0,0,0,0.6), 0 1px 0 rgba(255,255,255,0.02) inset !important;
}

/* ── TRACE PANEL ─────────────────────────────────────────── */
.trace-panel,
.trace-panel > .wrap,
.trace-panel > div {
    background: #070910 !important;
    border: none !important;
    border-right: 1px solid #141830 !important;
    padding: 0 !important;
    margin: 0 !important;
    height: 620px !important;
    max-height: 620px !important;
    overflow: hidden !important;
}
.trace-panel label { display: none !important; }

.trace-panel-header {
    padding: 9px 14px;
    font-size: 0.65rem;
    font-weight: 700;
    color: #2a3560;
    border-bottom: 1px solid #111830;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    font-family: 'Courier New', monospace;
    background: linear-gradient(180deg, #0a0d1c 0%, #070910 100%);
    position: sticky;
    top: 0;
    box-shadow: 0 2px 10px rgba(0,0,0,0.4);
}
.trace-panel-inner {
    padding: 10px 8px;
    overflow-y: auto;
    height: calc(620px - 35px);
}

/* ── CHAT COLUMN ─────────────────────────────────────────── */
.chat-col {
    background: #070910 !important;
    border: none !important;
    padding: 8px !important;
    height: 620px !important;
    max-height: 620px !important;
    display: flex !important;
    flex-direction: column !important;
    overflow: hidden !important;
}
.chat-col > .wrap {
    background: #070910 !important;
    border: none !important;
    height: 100% !important;
    display: flex !important;
    flex-direction: column !important;
}

/* ── CHATBOT ─────────────────────────────────────────────── */
.chatbot-box { flex: 1 1 auto !important; min-height: 0 !important; background: #070910 !important; border: none !important; }
.chatbot-box > .wrap { background: #070910 !important; border: none !important; height: 100% !important; }
.chatbot-box > div { background: #070910 !important; border: none !important; }

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
    background: linear-gradient(135deg, #0d1020 0%, #0a0d1a 100%) !important;
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
    background: linear-gradient(145deg, #0f0d28 0%, #0c0b22 60%, #090918 100%) !important;
    border: 1px solid #241e50 !important;
    border-top: 1px solid #2e2860 !important;
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
    color: #7c6fe0 !important;
    border: 1px solid #1e1a40 !important;
    border-radius: 4px !important;
    padding: 1px 6px !important;
    font-family: 'Courier New', Consolas, monospace !important;
    font-size: 0.83em !important;
}
.chatbot-box pre {
    background: #0a081e !important;
    border: 1px solid #1e1a40 !important;
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
    margin-top: 6px !important;
    box-shadow: 0 2px 14px rgba(124,111,224,0.2) !important;
}
.input-wrap > div,
.input-wrap .block,
.input-wrap .form {
    background: transparent !important;
    padding: 0 !important;
    border: none !important;
    box-shadow: none !important;
    gap: 4px !important;
}
.input-wrap .gap { gap: 4px !important; }
.input-wrap textarea {
    background: #0b0e1e !important;
    color: #c8d4f0 !important;
    border: none !important;
    border-radius: 9px !important;
    caret-color: #7c6fe0 !important;
    min-height: 44px !important;
    max-height: 44px !important;
    padding: 10px 14px !important;
    font-size: 0.92rem !important;
    font-family: 'Inter', 'Segoe UI', sans-serif !important;
    resize: none !important;
}
.input-wrap textarea::placeholder { color: #2a3050 !important; }

/* ── SEND BUTTON ─────────────────────────────────────────── */
.send-btn > div, .send-btn > .wrap { background: transparent !important; border: none !important; padding: 0 !important; }
.send-btn button {
    background: linear-gradient(180deg, #5a4fd0 0%, #4035b0 100%) !important;
    border-radius: 9px !important;
    border: 1px solid #6a5ee0 !important;
    border-bottom: 1px solid #2a2090 !important;
    color: #e8e4ff !important;
    font-weight: 600 !important;
    font-family: 'Inter', 'Segoe UI', sans-serif !important;
    letter-spacing: 0.04em !important;
    box-shadow: 0 4px 14px rgba(60,40,180,0.35), 0 1px 0 rgba(180,160,255,0.12) inset !important;
    height: 44px !important;
    min-height: 44px !important;
    font-size: 0.88rem !important;
    cursor: pointer !important;
    transition: all 0.15s ease !important;
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
"""

# ── Trace HTML builder ─────────────────────────────────────────────────────────

TYPE_COLORS = {
    "node_exec":    {"bg": "#040d0d", "border": "#0a3030", "label_color": "#00d4d4",  "arrow_color": "#00d4d4"},
    "tool_call":    {"bg": "#040d18", "border": "#0a2545", "label_color": "#3b82f6",  "arrow_color": "#3b82f6"},
    "tool_result":  {"bg": "#080818", "border": "#181840", "label_color": "#7c6fe0",  "arrow_color": "#7c6fe0"},
    "llm_response": {"bg": "#0d0820", "border": "#22145a", "label_color": "#a78bfa",  "arrow_color": "#a78bfa"},
    "graph_call":   {"bg": "#100c04", "border": "#3a2008", "label_color": "#f97316",  "arrow_color": "#f97316"},
    "graph_result": {"bg": "#0c0a04", "border": "#2a1c04", "label_color": "#fbbf24",  "arrow_color": "#fbbf24"},
}


def build_trace_step(i: int, entry: dict) -> str:
    colors = TYPE_COLORS.get(entry["type"], TYPE_COLORS["llm_response"])
    content = entry.get("content", "")[:100]
    label = entry.get("label", "")
    from_ = entry.get("from", "")
    to_ = entry.get("to", "")
    arrow = entry.get("arrow", "->")

    return f"""
    <div style='background:{colors["bg"]}; border:1px solid {colors["border"]};
                border-left:2px solid {colors["border"]};
                border-radius:8px; padding:8px 10px; margin-bottom:5px;
                font-family:"Courier New",Consolas,monospace; font-size:0.73rem;
                box-shadow:0 2px 8px rgba(0,0,0,0.3);'>
        <div style='display:flex; align-items:center; gap:6px; margin-bottom:4px;'>
            <span style='color:#1e2545; font-size:0.62rem;'>#{i:02d}</span>
            <span style='color:#8090c0; font-weight:600;'>{from_}</span>
            <span style='color:{colors["arrow_color"]}; font-size:0.9rem; opacity:0.8;'>{arrow}</span>
            <span style='color:#8090c0; font-weight:600;'>{to_}</span>
            <span style='margin-left:auto; border:1px solid {colors["border"]};
                         color:{colors["label_color"]}; border-radius:4px;
                         padding:1px 7px; font-size:0.6rem; letter-spacing:0.06em;
                         text-transform:uppercase;'>{label}</span>
        </div>
        <div style='color:#3a456a; font-size:0.68rem; word-break:break-all;
                    border-top:1px solid {colors["border"]}; padding-top:4px; margin-top:2px;
                    line-height:1.4;'>
            {content if content else "<i style='color:#1a2040; font-style:italic;'>no content</i>"}
        </div>
    </div>"""


def build_agent_card(agent_name: str) -> str:
    agent_type = META.get(agent_name, {}).get("type", "chat")
    return f"""
    <div style='background:linear-gradient(145deg,#0f0d28,#0c0b22,#090918);
                border:1px solid #241e50; border-top:1px solid #2e2860;
                border-left:3px solid #7c6fe0;
                border-radius:10px; padding:11px 14px; margin-bottom:10px;
                box-shadow:0 4px 20px rgba(60,40,160,0.2), 0 1px 0 rgba(140,120,255,0.05) inset;'>
        <div style='display:flex; justify-content:space-between; align-items:center;'>
            <span style='color:#c8d0f0; font-weight:700; font-size:0.85rem;'>{agent_name}</span>
            <span style='background:rgba(0,212,212,0.08); border:1px solid rgba(0,212,212,0.2);
                         border-radius:10px; padding:2px 8px;
                         color:#00d4d4; font-size:0.62rem; font-family:monospace; letter-spacing:0.06em;'>&#9679; {agent_type.upper()}</span>
        </div>
        <div style='margin-top:5px; font-size:0.67rem; color:#2a3060; font-family:monospace; letter-spacing:0.04em;'>
            // MODEL: <span style='color:#7c6fe0;'>LangGraph 1.1.3</span>
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
        return "", history, build_trace_html(agent_name)
    run_fn = AGENTS[agent_name]
    reply = run_fn(user_message) or ""
    history = history + [
        {"role": "user", "content": user_message},
        {"role": "assistant", "content": reply},
    ]
    return "", history, build_trace_html(agent_name)


# ── UI Layout ──────────────────────────────────────────────────────────────────

with gr.Blocks(title="Agent Studio") as demo:

    gr.HTML("""
    <div class='app-header'>
        <h2>Agentic AI Playground</h2>
    </div>
    """)

    agent_selector = gr.Dropdown(
        choices=list(AGENTS.keys()),
        value=list(AGENTS.keys())[0] if AGENTS else None,
        label="Active Agent",
        elem_classes=["agent-dropdown"],
    )

    with gr.Row(elem_classes=["main-row"]):

        with gr.Column(scale=2, min_width=270, elem_classes=["trace-panel"]):
            debug_panel = gr.HTML(
                value=build_trace_html(list(AGENTS.keys())[0]) if AGENTS else "",
                label="",
            )

        with gr.Column(scale=5, elem_classes=["chat-col"]):
            chatbot = gr.Chatbot(
                label="",
                height=520,
                show_label=False,
                elem_classes=["chatbot-box"],
            )
            with gr.Group(elem_classes=["input-wrap"]):
                with gr.Row():
                    user_input = gr.Textbox(
                        placeholder="Type your message...",
                        label="",
                        show_label=False,
                        scale=9,
                    )
                    send_btn = gr.Button("Send", scale=1, variant="primary", elem_classes=["send-btn"])

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
