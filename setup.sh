#!/bin/bash
# ──────────────────────────────────────────────────────────────────────────────
# AI Playground — Setup Script (Linux / macOS)
#
# Run from the project root (after cloning):
#   chmod +x setup.sh && ./setup.sh
#
# What it does:
#   1. Checks Python 3.12+ is installed
#   2. Creates virtual environment (.venv)
#   3. Installs all dependencies from requirements.txt
#   4. Creates .env from template and prompts for credentials
#   5. Verifies the installation works
#   6. Shows how to start the Studio
# ──────────────────────────────────────────────────────────────────────────────

set -e

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
WHITE='\033[1;37m'
GRAY='\033[0;37m'
NC='\033[0m' # No Color

echo ""
echo -e "${CYAN}AI Playground — Setup${NC}"
echo -e "${CYAN}==============================${NC}"
echo ""

# ── Step 1: Check Python ──────────────────────────────────────────────────────

echo -e "${YELLOW}[1/5] Checking Python...${NC}"

PYTHON_CMD=""
for cmd in python3.12 python3 python; do
    if command -v "$cmd" &>/dev/null; then
        VERSION=$("$cmd" --version 2>&1)
        if [[ "$VERSION" =~ Python\ 3\.([0-9]+) ]]; then
            MINOR="${BASH_REMATCH[1]}"
            if [ "$MINOR" -ge 12 ]; then
                PYTHON_CMD="$cmd"
                echo -e "  ${GREEN}Found: $VERSION${NC}"
                break
            fi
        fi
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo -e "  ${RED}Python 3.12+ not found.${NC}"
    echo -e "  ${GRAY}Install with: sudo apt install python3.12  (Debian/Ubuntu)${NC}"
    echo -e "  ${GRAY}           or: brew install python@3.12    (macOS)${NC}"
    exit 1
fi

# ── Step 2: Create virtual environment ───────────────────────────────────────

echo -e "${YELLOW}[2/5] Setting up virtual environment...${NC}"

if [ -d ".venv" ]; then
    echo -e "  ${GREEN}.venv already exists - reusing${NC}"
else
    "$PYTHON_CMD" -m venv .venv
    if [ ! -d ".venv" ]; then
        echo -e "  ${RED}Failed to create .venv${NC}"
        exit 1
    fi
    echo -e "  ${GREEN}.venv created${NC}"
fi

source .venv/bin/activate
echo -e "  ${GREEN}Activated${NC}"

# ── Step 3: Install dependencies ─────────────────────────────────────────────

echo -e "${YELLOW}[3/5] Installing dependencies...${NC}"
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
echo -e "  ${GREEN}All packages installed${NC}"

# ── Step 4: Setup .env ───────────────────────────────────────────────────────

echo -e "${YELLOW}[4/5] Configuring .env...${NC}"

if [ -f ".env" ]; then
    echo -e "  ${GREEN}.env already exists - keeping${NC}"
else
    cp .env.example .env
    echo -e "  ${GREEN}Created .env from template${NC}"
    echo ""
    echo -e "  ${CYAN}Let's configure your credentials. Press Enter to skip any field.${NC}"
    echo ""

    # LLM API Key
    read -rp "  LLM_API_KEY (your LiteLLM proxy API key): " api_key
    if [ -n "$api_key" ]; then
        sed -i "s|LLM_API_KEY=.*|LLM_API_KEY=${api_key}|" .env
        echo -e "  ${GREEN}LLM_API_KEY saved${NC}"
    fi

    # LLM Proxy URL
    read -rp "  LLM_PROXY (proxy URL, e.g. https://litellm.example.com): " proxy_url
    if [ -n "$proxy_url" ]; then
        sed -i "s|LLM_PROXY=.*|LLM_PROXY=${proxy_url}|" .env
        echo -e "  ${GREEN}LLM_PROXY saved${NC}"
    fi

    # LLM Model
    read -rp "  LLM_MODEL [gpt-5.4-nano]: " model
    if [ -n "$model" ]; then
        sed -i "s|LLM_MODEL=.*|LLM_MODEL=${model}|" .env
        echo -e "  ${GREEN}LLM_MODEL saved${NC}"
    fi

    # Langfuse (optional)
    echo ""
    echo -e "  ${WHITE}Langfuse (observability/tracing) - optional, press Enter to skip:${NC}"

    read -rp "  LANGFUSE_PROXY (e.g. https://langfuse.example.com): " lf_proxy
    if [ -n "$lf_proxy" ]; then
        sed -i "s|LANGFUSE_PROXY=.*|LANGFUSE_PROXY=${lf_proxy}|" .env
    fi

    read -rp "  LANGFUSE_PUBLIC_KEY: " lf_pub
    if [ -n "$lf_pub" ]; then
        sed -i "s|LANGFUSE_PUBLIC_KEY=.*|LANGFUSE_PUBLIC_KEY=${lf_pub}|" .env
    fi

    read -rp "  LANGFUSE_SECRET_KEY: " lf_sec
    if [ -n "$lf_sec" ]; then
        sed -i "s|LANGFUSE_SECRET_KEY=.*|LANGFUSE_SECRET_KEY=${lf_sec}|" .env
    fi

    echo ""
    echo -e "  ${GREEN}.env configured! Edit anytime with: code .env${NC}"
fi

# ── Step 5: Verify ────────────────────────────────────────────────────────────

echo -e "${YELLOW}[5/5] Verifying installation...${NC}"

if python -c "import langgraph; import langchain_openai; import gradio; import fastapi; print('OK')" 2>/dev/null | grep -q "OK"; then
    echo -e "  ${GREEN}All packages verified${NC}"
else
    echo -e "  ${RED}Verification failed. Try: pip install -r requirements.txt${NC}"
    exit 1
fi

# ── Done ──────────────────────────────────────────────────────────────────────

echo ""
echo -e "${CYAN}==============================${NC}"
echo -e "${GREEN}Setup complete!${NC}"
echo -e "${CYAN}==============================${NC}"
echo ""
echo -e "${WHITE}Next steps:${NC}"
echo ""
echo -e "  ${YELLOW}1. Activate the environment (every new terminal):${NC}"
echo -e "     ${CYAN}source .venv/bin/activate${NC}"
echo ""
echo -e "  ${YELLOW}2. Start the Studio UI:${NC}"
echo -e "     ${CYAN}python studio.py${NC}"
echo ""
echo -e "  ${YELLOW}3. Open browser: http://localhost:8000${NC}"
echo ""
echo -e "  ${YELLOW}4. Start Learn Mode in Copilot Chat:${NC}"
echo -e "     ${CYAN}Learn Mode — I want to build agent_hello.py${NC}"
echo ""
echo -e "  ${GRAY}See Learn/GETTING_STARTED.md for the full guide.${NC}"
echo ""

# ── Open VS Code ─────────────────────────────────────────────────────────────

if command -v code &>/dev/null; then
    code .
    echo -e "${GREEN}VS Code opened in current folder.${NC}"
else
    echo -e "${YELLOW}Could not open VS Code automatically. Open it manually: code .${NC}"
fi
echo ""
