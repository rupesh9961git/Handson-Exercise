#!/bin/bash
trap 'kill 0' EXIT

# free port 5173 if still occupied
lsof -ti:5173 | xargs kill -9 2>/dev/null

.venv/bin/uvicorn server:app --reload --port 8000 &
cd ui && npm run dev
