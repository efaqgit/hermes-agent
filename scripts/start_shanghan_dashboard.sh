#!/usr/bin/env bash
# Start the Standalone TCM Shanghan Dashboard (Port 9300)

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=========================================================="
echo "🌿 Starting Traditional Chinese Medicine (Shanghan) Dashboard"
echo "=========================================================="
echo "Initializing FastAPI Backend on Port 9300..."

cd "$ROOT_DIR" || exit 1

# Activate virtual environment if it exists
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
elif [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
else
    echo "Warning: No virtual environment found. Using system python."
fi

# Run the Uvicorn server directly from the module
python plugins/shanghan/server.py
