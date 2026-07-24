#!/bin/bash
# Startup script: seed database on first run, then start server
set -e
if [ ! -f /app/db.sqlite3 ] || [ ! -s /app/db.sqlite3 ]; then
    echo "Seeding database..."
    python /app/seed.py
fi
exec uvicorn app.main:app --host 0.0.0.0 --port 8000# auto-deploy test
