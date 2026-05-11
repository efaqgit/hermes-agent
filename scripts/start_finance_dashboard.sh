#!/bin/bash
# Standalone Financial Dashboard Starter Script
# Runs the independent FastAPI server on port 9200 using local python environment.

# Resolve workspace directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
WORKSPACE_DIR="$(dirname "$SCRIPT_DIR")"

cd "$WORKSPACE_DIR"

echo "⚡ Launching Standalone Unified Finance Terminal via venv..."
venv/bin/python plugins/finance_dashboard_standalone/server.py
