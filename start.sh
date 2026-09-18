#!/usr/bin/env bash
# ==============================================================================
# SHILL: Unified Zero-Touch Autonomous Build, Install & Launcher
# Supports:
#   ./start.sh                -> Install if needed & run the sovereign node
#   ./start.sh --install-only -> Setup venv & install dependencies only
#   ./start.sh --build        -> Re-install / rebuild environment & dependencies
#   ./start.sh --version      -> Display version
#   ./start.sh --help         -> Show usage
# ==============================================================================
set -e

VERSION="0.2.0"
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

show_help() {
    echo -e "${GREEN}SHILL v${VERSION}${NC} — Sovereign Autonomous P2P Bot Mesh & AMM DEX"
    echo ""
    echo "Usage: ./start.sh [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --install-only    Prepare environment and install dependencies without starting server"
    echo "  --build           Force-rebuild/upgrade virtualenv and python dependencies"
    echo "  --version, -v     Print current Shill version"
    echo "  --help, -h        Show this help message"
    echo ""
    echo "Environment Variables:"
    echo "  PORT              HTTP/WebSocket port (default: 8000)"
    echo "  UDP_PORT          P2P datagram mesh port (default: 9999)"
    echo "  SHILL_VERSION     Custom version override (default: 0.2.0)"
    echo ""
}

# Handle quick flag checks
if [[ "$1" == "--version" || "$1" == "-v" ]]; then
    echo "shill v${VERSION}"
    exit 0
fi

if [[ "$1" == "--help" || "$1" == "-h" ]]; then
    show_help
    exit 0
fi

FORCE_BUILD=0
INSTALL_ONLY=0

for arg in "$@"; do
    case "$arg" in
        --build)
            FORCE_BUILD=1
            ;;
        --install-only)
            INSTALL_ONLY=1
            ;;
    esac
done

echo -e "${BLUE}===================================================================${NC}"
echo -e "${GREEN}       🤖 SHILL v${VERSION}: Sovereign Autonomous P2P Bot Mesh & DEX  ${NC}"
echo -e "${BLUE}===================================================================${NC}"

# 1. Verify Python 3 presence
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}[ERROR] python3 is required but not installed. Please install Python 3.10+${NC}"
    exit 1
fi

PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo -e "${GREEN}✓ Python environment: ${PY_VERSION}${NC}"

# 2. Setup Virtual Environment if missing or force build
if [[ "$FORCE_BUILD" -eq 1 && -d "venv" ]]; then
    echo -e "${YELLOW}Rebuilding virtual environment (--build flag active)...${NC}"
    rm -rf venv
fi

if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating isolated virtual environment in ./venv...${NC}"
    python3 -m venv venv
fi

source venv/bin/activate

# 3. Check and install core dependencies
NEEDS_INSTALL=0
if [[ "$FORCE_BUILD" -eq 1 ]]; then
    NEEDS_INSTALL=1
elif ! python3 -c "import fastapi, uvicorn, tonsdk, nacl" 2>/dev/null; then
    NEEDS_INSTALL=1
fi

if [[ "$NEEDS_INSTALL" -eq 1 ]]; then
    echo -e "${YELLOW}Installing core dependencies and cryptographic libraries...${NC}"
    pip install --upgrade pip --quiet
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt --quiet
    else
        pip install fastapi uvicorn websockets pydantic jinja2 requests aiohttp textstat pytest pyotp tonsdk pynacl ecdsa --quiet
    fi
    echo -e "${GREEN}✓ Dependencies installed successfully.${NC}"
else
    echo -e "${GREEN}✓ Dependencies verified.${NC}"
fi

# 4. Ensure required storage directories exist
mkdir -p data data/routines training

# 5. Secure first-run credential bootstrap
if [ ! -f ".env" ]; then
    _ROOT_PW=$(python3 -c "import secrets; print(secrets.token_urlsafe(20))")
    _TOTP_SECRET=$(python3 -c "import secrets,base64; print(base64.b32encode(secrets.token_bytes(20)).decode())")
    _SALT=$(python3 -c "import secrets; print(secrets.token_hex(16))")
    _HASH=$(SHILL_PW="$_ROOT_PW" SHILL_SALT="$_SALT" python3 -c "import os,hashlib; print(hashlib.pbkdf2_hmac('sha256', os.environ['SHILL_PW'].encode(), os.environ['SHILL_SALT'].encode(), 100000).hex())")
    _VAULT=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    {
        echo "SHILL_ROOT_USER=root_admin"
        echo "SHILL_ROOT_PASSWORD_HASH=$_HASH"
        echo "SHILL_ROOT_SALT=$_SALT"
        echo "SHILL_ROOT_TOTP_SECRET=$_TOTP_SECRET"
        echo "SHILL_VAULT_KEY=$_VAULT"
        echo "SHILL_VERSION=$VERSION"
    } > .env
    chmod 600 .env
    echo -e "${GREEN}[SECURITY] Generated fresh superuser + vault credentials in .env (mode 600).${NC}"
    echo -e "${YELLOW}[SECURITY] Root password: $_ROOT_PW${NC}"
    echo -e "${YELLOW}[SECURITY] Store the root password + TOTP secret in your password manager NOW. It is never printed again.${NC}"
fi

set -a; [ -f .env ] && source .env; set +a
: "${SHILL_ALLOW_INSECURE_DEFAULTS:=0}"
export SHILL_ALLOW_INSECURE_DEFAULTS
export SHILL_VERSION="${SHILL_VERSION:-$VERSION}"

if [[ "$INSTALL_ONLY" -eq 1 ]]; then
    echo -e "${GREEN}✓ Build & Installation complete! Run ./start.sh to launch.${NC}"
    exit 0
fi

# 6. Launch Sovereign Peer Node
PORT="${PORT:-8000}"
UDP_PORT="${UDP_PORT:-9999}"

echo -e "${BLUE}===================================================================${NC}"
echo -e "${GREEN}       🚀 Launching Sovereign Node & Self-Loading Mesh             ${NC}"
echo -e "${BLUE}===================================================================${NC}"
echo -e "${CYAN}• Version:${NC}                  v${SHILL_VERSION}"
echo -e "${CYAN}• Web UI & AMM DEX:${NC}         http://localhost:${PORT}"
echo -e "${CYAN}• Sovereign UDP Mesh:${NC}       0.0.0.0:${UDP_PORT} (Self-Loading Beacon)"
echo -e "${CYAN}• OpenAI Compatible API:${NC}    http://localhost:${PORT}/v1/chat/completions"
echo -e "${CYAN}• Democratize AI Portal:${NC}    http://localhost:${PORT}/#democratize (100 Free Citizen Queries/Day)"
echo -e "${CYAN}• Hardened Hive Shield:${NC}     http://localhost:${PORT}/#shield (Zero-Quarter Corporate Poison Defense)"
echo -e "${CYAN}• Forensic On-Chain Badges:${NC} ton-mainnet-v4r2 (0x... Verifiable Agent Signatures)"
echo -e "${CYAN}• Public Sniffer:${NC}           http://localhost:${PORT}/#telemetry"
echo -e "${CYAN}• Superuser 2FA Visualizer:${NC} root_admin / <see .env first-run output>"
echo -e "${BLUE}===================================================================${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop node.${NC}"
echo ""

export PYTHONPATH=.
export UDP_PORT="${UDP_PORT}"
exec python3 backend/main.py
