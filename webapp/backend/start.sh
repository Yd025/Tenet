#!/bin/bash
# Start all Tenet services
# Run from repo root: ./webapp/backend/start.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

echo "=== Starting Tenet Services ==="

# 1. Start uagents (in background)
echo "[1/3] Starting uagents..."
cd "$REPO_ROOT/tenet-agents"
python run_all_agents.py &
AGENTS_PID=$!
echo "  → uagents PID: $AGENTS_PID"

# Wait for agents to initialize
sleep 3

# 2. Start FastAPI backend (in background)
echo "[2/3] Starting FastAPI backend..."
cd "$REPO_ROOT/webapp/backend"
source .venv/bin/activate 2>/dev/null || true
uvicorn main:app --reload --port 8000 &
FASTAPI_PID=$!
echo "  → FastAPI PID: $FASTAPI_PID"

# 3. Start frontend dev server (in background)
echo "[3/3] Starting frontend..."
cd "$REPO_ROOT/webapp/frontend"
npm run dev &
FRONTEND_PID=$!
echo "  → Frontend PID: $FRONTEND_PID"

echo ""
echo "=== All services running ==="
echo "  Frontend:  http://localhost:5173"
echo "  API:       http://localhost:8000"
echo "  Agents:    ports 8001-8005"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait and cleanup
trap "kill $AGENTS_PID $FASTAPI_PID $FRONTEND_PID 2>/dev/null; exit 0" SIGINT SIGTERM
wait
