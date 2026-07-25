#!/bin/bash
# KH07 Welfare — startup script
# Seeds the database if /data/db.sqlite3 doesn't exist, then starts uvicorn.

set -e

# Ensure data directory exists
mkdir -p /data

# Seed database if it doesn't exist
if [ ! -f /data/db.sqlite3 ]; then
    echo "No database found at /data/db.sqlite3 — seeding..."
    python seed.py
    echo "Seed complete"
else
    echo "Database exists at /data/db.sqlite3 — skipping seed"
fi

# Start uvicorn
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
