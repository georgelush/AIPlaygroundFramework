# ──────────────────────────────────────────────────────────────────────────────
# AI Playground — Setup Script (Windows PowerShell)
#
# Run from the project root (after cloning):
#   .\setup.ps1
#
# What it does:
#   1. Checks Python 3.12+ is installed
#   2. Creates virtual environment (.venv)
#   3. Installs all dependencies from requirements.txt
#   4. Creates .env from template and prompts for credentials
#   5. Verifies the installation works
#   6. Shows how to start the Studio
# ──────────────────────────────────────────────────────────────────────────────

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "AI Playground - Setup" -ForegroundColor Cyan
Write-Host "==============================" -ForegroundColor Cyan
Write-Host ""

# ── Step 1: Check Python ──────────────────────────────────────────────────────

Write-Host "[1/5] Checking Python..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    if ($pythonVersion -match 'Python 3\.(\d+)') {
        $minor = [int]$matches[1]
        if ($minor -lt 12) {
            Write-Host "  Python 3.12+ required. You have: $pythonVersion" -ForegroundColor Red
            Write-Host '  Install from: winget install -e --id Python.Python.3.12' -ForegroundColor Gray
            exit 1
        }
    }
    Write-Host "  Found: $pythonVersion" -ForegroundColor Green
}
catch {
    Write-Host "  Python not found." -ForegroundColor Red
    Write-Host '  Run as Administrator: winget install -e --id Python.Python.3.12' -ForegroundColor Yellow
    exit 1
}

# ── Step 2: Create virtual environment ───────────────────────────────────────

Write-Host "[2/5] Setting up virtual environment..." -ForegroundColor Yellow
if (Test-Path ".venv") {
    Write-Host "  .venv already exists - reusing" -ForegroundColor Green
}
else {
    python -m venv .venv
    if (-not (Test-Path ".venv")) {
        Write-Host "  Failed to create .venv" -ForegroundColor Red
        exit 1
    }
    Write-Host "  .venv created" -ForegroundColor Green
}

& .\.venv\Scripts\Activate.ps1
Write-Host "  Activated" -ForegroundColor Green

# ── Step 3: Install dependencies ─────────────────────────────────────────────

Write-Host "[3/5] Installing dependencies..." -ForegroundColor Yellow
$ErrorActionPreference = "Continue"

# Check if uv is already installed
$uvVersion = uv --version 2>$null
$useUv = $false

if ($uvVersion) {
    Write-Host "  uv already installed: $uvVersion" -ForegroundColor Green
    $useUv = $true
} else {
    Write-Host "  uv not found - installing uv (fast package manager)..." -ForegroundColor Yellow
    python -m pip install --upgrade pip --quiet 2>$null
    python -m pip install uv --quiet 2>$null
    $uvVersion = uv --version 2>$null
    if ($uvVersion) {
        Write-Host "  uv installed: $uvVersion" -ForegroundColor Green
        $useUv = $true
    } else {
        Write-Host "  uv install failed - falling back to pip" -ForegroundColor Yellow
    }
}

if ($useUv) {
    uv pip install -r requirements.txt
} else {
    pip install -r requirements.txt --quiet
}

$ErrorActionPreference = "Stop"
Write-Host "  All packages installed" -ForegroundColor Green

# ── Step 4: Setup .env ───────────────────────────────────────────────────────

Write-Host "[4/5] Configuring .env..." -ForegroundColor Yellow

if (Test-Path ".env") {
    Write-Host "  .env already exists - keeping" -ForegroundColor Green
}
else {
    Copy-Item ".env.example" ".env"
    Write-Host "  Created .env from template" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Let's configure your credentials. Press Enter to skip any field." -ForegroundColor Cyan
    Write-Host ""

    # LLM API Key
    $apiKey = Read-Host "  LLM_API_KEY (your LiteLLM proxy API key)"
    if ($apiKey -and $apiKey.Trim() -ne '') {
        $envContent = Get-Content ".env" -Raw -Encoding UTF8
        $envContent = $envContent -replace 'LLM_API_KEY=.*', "LLM_API_KEY=$($apiKey.Trim())"
        $envContent | Set-Content ".env" -NoNewline -Encoding UTF8
        Write-Host "  LLM_API_KEY saved" -ForegroundColor Green
    }

    # LLM Proxy URL
    $proxyUrl = Read-Host "  LLM_PROXY (proxy URL, e.g. https://litellm.example.com)"
    if ($proxyUrl -and $proxyUrl.Trim() -ne '') {
        $envContent = Get-Content ".env" -Raw -Encoding UTF8
        $envContent = $envContent -replace 'LLM_PROXY=.*', "LLM_PROXY=$($proxyUrl.Trim())"
        $envContent | Set-Content ".env" -NoNewline -Encoding UTF8
        Write-Host "  LLM_PROXY saved" -ForegroundColor Green
    }

    # LLM Model
    $model = Read-Host "  LLM_MODEL [gpt-5.4-nano]"
    if ($model -and $model.Trim() -ne '') {
        $envContent = Get-Content ".env" -Raw -Encoding UTF8
        $envContent = $envContent -replace 'LLM_MODEL=.*', "LLM_MODEL=$($model.Trim())"
        $envContent | Set-Content ".env" -NoNewline -Encoding UTF8
        Write-Host "  LLM_MODEL saved" -ForegroundColor Green
    }

    # Langfuse (optional)
    Write-Host ""
    Write-Host "  Langfuse (observability/tracing) - optional, press Enter to skip:" -ForegroundColor White
    $lfProxy = Read-Host "  LANGFUSE_PROXY (e.g. https://langfuse.example.com)"
    if ($lfProxy -and $lfProxy.Trim() -ne '') {
        $envContent = Get-Content ".env" -Raw -Encoding UTF8
        $envContent = $envContent -replace 'LANGFUSE_PROXY=.*', "LANGFUSE_PROXY=$($lfProxy.Trim())"
        $envContent | Set-Content ".env" -NoNewline -Encoding UTF8
    }
    $lfPub = Read-Host "  LANGFUSE_PUBLIC_KEY"
    if ($lfPub -and $lfPub.Trim() -ne '') {
        $envContent = Get-Content ".env" -Raw -Encoding UTF8
        $envContent = $envContent -replace 'LANGFUSE_PUBLIC_KEY=.*', "LANGFUSE_PUBLIC_KEY=$($lfPub.Trim())"
        $envContent | Set-Content ".env" -NoNewline -Encoding UTF8
    }
    $lfSec = Read-Host "  LANGFUSE_SECRET_KEY"
    if ($lfSec -and $lfSec.Trim() -ne '') {
        $envContent = Get-Content ".env" -Raw -Encoding UTF8
        $envContent = $envContent -replace 'LANGFUSE_SECRET_KEY=.*', "LANGFUSE_SECRET_KEY=$($lfSec.Trim())"
        $envContent | Set-Content ".env" -NoNewline -Encoding UTF8
    }

    Write-Host ""
    Write-Host "  .env configured! Edit anytime with: code .env" -ForegroundColor Green
}

# ── Step 5: Verify ────────────────────────────────────────────────────────────

Write-Host "[5/5] Verifying installation..." -ForegroundColor Yellow
$ErrorActionPreference = "Continue"
$verify = python -c "import langgraph; import langchain_openai; import gradio; import fastapi; print('OK')" 2>&1
$ErrorActionPreference = "Stop"

if ($verify -match "OK") {
    Write-Host "  All packages verified" -ForegroundColor Green
}
else {
    Write-Host "  Verification failed:" -ForegroundColor Red
    Write-Host "  $verify" -ForegroundColor Red
    Write-Host "  Try: pip install -r requirements.txt" -ForegroundColor Yellow
    exit 1
}

# ── Done ──────────────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "==============================" -ForegroundColor Cyan
Write-Host "Setup complete!" -ForegroundColor Green
Write-Host "==============================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor White
Write-Host ""
Write-Host "  1. Activate the environment (every new terminal):" -ForegroundColor Yellow
Write-Host "     .\.venv\Scripts\activate" -ForegroundColor Cyan
Write-Host ""
Write-Host "  2. Start the Studio UI:" -ForegroundColor Yellow
Write-Host "     python studio.py" -ForegroundColor Cyan
Write-Host ""
Write-Host "  3. Open browser: http://localhost:8000" -ForegroundColor Yellow
Write-Host ""
Write-Host "  4. Start Learn Mode in Copilot Chat:" -ForegroundColor Yellow
Write-Host '     Learn Mode — I want to build agent_hello.py' -ForegroundColor Cyan
Write-Host ""
Write-Host "See Learn/GETTING_STARTED.md for the full guide." -ForegroundColor Gray
Write-Host ""

# ── Open VS Code ─────────────────────────────────────────────────────────────

try {
    code .
    Write-Host "VS Code opened in current folder." -ForegroundColor Green
}
catch {
    Write-Host "Could not open VS Code automatically. Open it manually: code ." -ForegroundColor Yellow
}
Write-Host ""
