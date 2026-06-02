#!/bin/bash
set -e

echo "Running Alembic migrations..."
cd /app && alembic upgrade head

echo "Starting FastAPI server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
