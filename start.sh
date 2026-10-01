#!/usr/bin/env bash
# Linux/container start script: apply schema, then run gunicorn bound to
# 0.0.0.0:${PORT:-8000}.
set -euo pipefail

cd "$(dirname "$0")"

PORT="${PORT:-8000}"

echo "Applying database schema..."
python apply_schema.py

echo "Starting gunicorn on 0.0.0.0:${PORT}..."
exec gunicorn --bind "0.0.0.0:${PORT}" --workers 4 wsgi:app
