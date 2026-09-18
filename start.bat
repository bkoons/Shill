@echo off
REM ==============================================================================
REM SHILL: Windows Launch & Installation Batch Script
REM Supports:
REM   start.bat               -> Install if needed & run the sovereign node
REM   start.bat --install-only -> Setup venv & install dependencies only
REM   start.bat --build        -> Force-rebuild environment & dependencies
REM   start.bat --version      -> Display version
REM ==============================================================================

setlocal enabledelayedexpansion

set VERSION=0.2.0
set PORT=8000
set UDP_PORT=9999
set SHILL_VERSION=0.2.0

if "%1"=="--version" (
    echo shill v%VERSION%
    exit /b 0
)
if "%1"=="-v" (
    echo shill v%VERSION%
    exit /b 0
)

if "%1"=="--help" (
    echo SHILL v%VERSION% - Sovereign Autonomous P2P Bot Mesh
    echo Usage: start.bat [--install-only] [--build] [--version]
    exit /b 0
)
if "%1"=="-h" (
    echo SHILL v%VERSION% - Sovereign Autonomous P2P Bot Mesh
    echo Usage: start.bat [--install-only] [--build] [--version]
    exit /b 0
)

set FORCE_BUILD=0
set INSTALL_ONLY=0

if "%1"=="--build" set FORCE_BUILD=1
if "%1"=="--install-only" set INSTALL_ONLY=1

echo ===================================================================
echo        SHILL v%VERSION%: Sovereign Autonomous P2P Bot Mesh (Windows)
echo ===================================================================

REM Check Python command
set PYTHON_CMD=python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    py --version >nul 2>&1
    if %errorlevel% equ 0 (
        set PYTHON_CMD=py
    ) else (
        echo [ERROR] Python 3.10+ is required but not installed or not in PATH.
        echo Please download and install Python from https://www.python.org/
        pause
        exit /b 1
    )
)

echo [OK] Python detected via: %PYTHON_CMD%

REM Setup Virtual Environment
if %FORCE_BUILD% equ 1 (
    if exist venv (
        echo Rebuilding virtual environment...
        rmdir /s /q venv
    )
)

if not exist venv (
    echo Creating isolated virtual environment in .\venv...
    %PYTHON_CMD% -m venv venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
)

call venv\Scripts\activate.bat

REM Check and install dependencies
set NEEDS_INSTALL=0
if %FORCE_BUILD% equ 1 set NEEDS_INSTALL=1

python -c "import fastapi, uvicorn, tonsdk, nacl" >nul 2>&1
if %errorlevel% neq 0 set NEEDS_INSTALL=1

if %NEEDS_INSTALL% equ 1 (
    echo Installing core dependencies and cryptographic libraries...
    python -m pip install --upgrade pip --quiet
    if exist requirements.txt (
        python -m pip install -r requirements.txt --quiet
    ) else (
        python -m pip install fastapi uvicorn websockets pydantic jinja2 requests aiohttp textstat pytest pyotp tonsdk pynacl ecdsa --quiet
    )
    echo [OK] Dependencies installed successfully.
) else (
    echo [OK] Dependencies verified.
)

REM Storage directories
if not exist data mkdir data
if not exist data\routines mkdir data\routines
if not exist training mkdir training

REM First-run credentials
if not exist .env (
    echo Generating secure first-run credentials in .env...
    python -c "import secrets, base64, hashlib, os; pw=secrets.token_urlsafe(20); salt=secrets.token_hex(16); h=hashlib.pbkdf2_hmac('sha256', pw.encode(), salt.encode(), 100000).hex(); totp=base64.b32encode(secrets.token_bytes(20)).decode(); vkey=secrets.token_urlsafe(32); f=open('.env','w'); f.write(f'SHILL_ROOT_USER=root_admin\nSHILL_ROOT_PASSWORD_HASH={h}\nSHILL_ROOT_SALT={salt}\nSHILL_ROOT_TOTP_SECRET={totp}\nSHILL_VAULT_KEY={vkey}\nSHILL_VERSION=%VERSION%\n'); f.close(); print(f'ROOT PASSWORD: {pw}')"
)

if %INSTALL_ONLY% equ 1 (
    echo [OK] Installation complete. Run start.bat to launch.
    exit /b 0
)

echo ===================================================================
echo        Launching Sovereign Node & Self-Loading Mesh (Windows)
echo ===================================================================
echo - Version:                  v%SHILL_VERSION%
echo - Web UI:                   http://localhost:%PORT%
echo - Sovereign UDP Mesh:       0.0.0.0:%UDP_PORT%
echo - OpenAI Compatible API:    http://localhost:%PORT%/v1/chat/completions
echo - Free Citizen Access:      http://localhost:%PORT%/#democratize
echo ===================================================================
echo Press Ctrl+C to stop node.
echo.

set PYTHONPATH=.
python backend\main.py

pause
