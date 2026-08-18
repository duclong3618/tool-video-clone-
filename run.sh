#!/bin/bash
# Author: DUC LONG
# VideoDubAI - Run Script

echo "========================================="
echo "  VideoDubAI - Starting..."
echo "========================================="

# Get script directory
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

# Activate venv
if [ -d "venv" ]; then
    source venv/Scripts/activate 2>/dev/null || source venv/bin/activate 2>/dev/null
fi

# Create .env if not exists
if [ ! -f .env ]; then
    cp .env.example .env
    echo "[OK] Created .env from .env.example"
fi

# Start backend in background
echo "[1/2] Starting backend on http://localhost:8000 ..."
uvicorn backend.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Start frontend in background
echo "[2/2] Starting frontend on http://localhost:3000 ..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "========================================="
echo "  VideoDubAI is running!"
echo "========================================="
echo ""
echo "  Frontend:  http://localhost:3000"
echo "  Backend:   http://localhost:8000"
echo "  Swagger:   http://localhost:8000/docs"
echo ""
echo "  Press Ctrl+C to stop"
echo "========================================="

# Wait for both
wait $BACKEND_PID $FRONTEND_PID
