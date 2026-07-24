#!/usr/bin/env bash
# Start local dev server with auto-reload
# Usage: ./dev.sh [port]

PORT="${1:-8001}"

# Kill anything on the port (including orphaned processes)
fuser -k "$PORT/tcp" 2>/dev/null

# Clear Python cache for clean imports
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null

# Start with auto-reload
exec venv/bin/python -m uvicorn app.main:app --reload --host 0.0.0.0 --port "$PORT"
