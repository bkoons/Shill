#!/usr/bin/env bash
# ==============================================================================
# SHILL: Unified Installer
# Delegates directly to ./start.sh with --install-only flag.
# Usage:
#   ./install.sh          -> Installs virtualenv, dependencies & bootstrapping
#   ./install.sh --build  -> Forces clean rebuild of environment & dependencies
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/start.sh" --install-only "$@"
