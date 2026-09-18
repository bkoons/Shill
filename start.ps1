# ==============================================================================
# SHILL: Modern Windows PowerShell Setup & Execution Script
# Supports:
#   .\start.ps1                -> Install if needed & run the sovereign node
#   .\start.ps1 -InstallOnly   -> Setup venv & install dependencies only
#   .\start.ps1 -Build         -> Force-rebuild environment & dependencies
#   .\start.ps1 -Version       -> Display version
# ==============================================================================
[CmdletBinding()]
param (
    [switch]$Build,
    [switch]$InstallOnly,
    [switch]$Version,
    [string]$Port = "8000",
    [string]$UdpPort = "9999"
)

$SHILL_VERSION = "0.2.0"

if ($Version) {
    Write-Host "shill v$SHILL_VERSION"
    exit 0
}

Write-Host "===================================================================" -ForegroundColor Cyan
Write-Host "       🤖 SHILL v$SHILL_VERSION: Sovereign Autonomous Bot Mesh (Windows) " -ForegroundColor Green
Write-Host "===================================================================" -ForegroundColor Cyan

# 1. Detect Python
$pythonCmd = $null
if (Get-Command python -ErrorAction SilentlyContinue) {
    $pythonCmd = "python"
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $pythonCmd = "py"
} else {
    Write-Host "[ERROR] Python 3.10+ is required but not installed." -ForegroundColor Red
    Write-Host "Please install Python from https://www.python.org/ or the Microsoft Store."
    exit 1
}

$pyVer = & $pythonCmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
Write-Host "✓ Python detected: $pyVer ($pythonCmd)" -ForegroundColor Green

# 2. Virtual Environment
if ($Build -and (Test-Path "venv")) {
    Write-Host "Rebuilding virtual environment (-Build active)..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force "venv"
}

if (-not (Test-Path "venv")) {
    Write-Host "Creating isolated virtual environment in .\venv..." -ForegroundColor Yellow
    & $pythonCmd -m venv venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Failed to create virtual environment." -ForegroundColor Red
        exit 1
    }
}

$venvPython = ".\venv\Scripts\python.exe"
$venvPip = ".\venv\Scripts\pip.exe"

# 3. Check Dependencies
$needsInstall = $false
if ($Build) {
    $needsInstall = $true
} else {
    & $venvPython -c "import fastapi, uvicorn, tonsdk, nacl" 2>$null
    if ($LASTEXITCODE -ne 0) {
        $needsInstall = $true
    }
}

if ($needsInstall) {
    Write-Host "Installing core dependencies and cryptographic libraries..." -ForegroundColor Yellow
    & $venvPython -m pip install --upgrade pip --quiet
    if (Test-Path "requirements.txt") {
        & $venvPip install -r requirements.txt --quiet
    } else {
        & $venvPip install fastapi uvicorn websockets pydantic jinja2 requests aiohttp textstat pytest pyotp tonsdk pynacl ecdsa --quiet
    }
    Write-Host "✓ Dependencies installed successfully." -ForegroundColor Green
} else {
    Write-Host "✓ Dependencies verified." -ForegroundColor Green
}

# 4. Storage Folders
New-Item -ItemType Directory -Force -Path "data", "data\routines", "training" | Out-Null

# 5. First-Run Credentials
if (-not (Test-Path ".env")) {
    Write-Host "Generating fresh superuser credentials in .env..." -ForegroundColor Yellow
    $genScript = @"
import secrets, base64, hashlib
pw = secrets.token_urlsafe(20)
salt = secrets.token_hex(16)
h = hashlib.pbkdf2_hmac('sha256', pw.encode(), salt.encode(), 100000).hex()
totp = base64.b32encode(secrets.token_bytes(20)).decode()
vkey = secrets.token_urlsafe(32)
with open('.env', 'w') as f:
    f.write(f'SHILL_ROOT_USER=root_admin\nSHILL_ROOT_PASSWORD_HASH={h}\nSHILL_ROOT_SALT={salt}\nSHILL_ROOT_TOTP_SECRET={totp}\nSHILL_VAULT_KEY={vkey}\nSHILL_VERSION=$SHILL_VERSION\n')
print(f'ROOT PASSWORD: {pw}')
"@
    & $venvPython -c $genScript
}

if ($InstallOnly) {
    Write-Host "✓ Installation complete! Run .\start.ps1 to launch." -ForegroundColor Green
    exit 0
}

# 6. Launch
Write-Host "===================================================================" -ForegroundColor Cyan
Write-Host "       🚀 Launching Sovereign Node & Self-Loading Mesh (Windows)   " -ForegroundColor Green
Write-Host "===================================================================" -ForegroundColor Cyan
Write-Host "• Version:                  v$SHILL_VERSION" -ForegroundColor Cyan
Write-Host "• Web UI & AMM DEX:         http://localhost:$Port" -ForegroundColor Cyan
Write-Host "• Sovereign UDP Mesh:       0.0.0.0:$UdpPort (Self-Loading Beacon)" -ForegroundColor Cyan
Write-Host "• OpenAI Compatible API:    http://localhost:$Port/v1/chat/completions" -ForegroundColor Cyan
Write-Host "• Democratize AI Portal:    http://localhost:$Port/#democratize" -ForegroundColor Cyan
Write-Host "===================================================================" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop node." -ForegroundColor Yellow
Write-Host ""

$env:PYTHONPATH = "."
$env:UDP_PORT = $UdpPort

& $venvPython backend\main.py
