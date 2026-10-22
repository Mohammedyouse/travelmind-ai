#!/usr/bin/env bash
# =============================================================================
# TravelMind AI — Render startup script
# Runs database migrations then starts the API server.
# =============================================================================
set -e

echo "[startup] Working directory: $(pwd)"
echo "[startup] Python: $(python --version)"
echo "[startup] DATABASE_URL scheme: ${DATABASE_URL%%://*}"

# Step 1: Run Alembic migrations (idempotent — safe to run on every deploy).
echo "[startup] Running database migrations..."
alembic upgrade head
echo "[startup] Migrations complete."

# Step 2: Start the API server.
echo "[startup] Starting uvicorn on port ${PORT:-8000}..."
exec uvicorn main:app \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" \
    --workers 1 \
    --log-level info \
    --access-log
