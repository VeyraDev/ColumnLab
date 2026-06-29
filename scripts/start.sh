#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "==> ColumnLab start (migrate + backend + frontend)"
cd "$ROOT/backend"
python -m alembic upgrade head
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 &
BACK_PID=$!
cd "$ROOT/frontend"
npm run dev &
FRONT_PID=$!
echo "Backend: http://127.0.0.1:8000  Frontend: http://127.0.0.1:5173"
echo "See docs/DEMO_SCRIPT.md for demo flow."
wait $BACK_PID $FRONT_PID
