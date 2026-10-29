#!/bin/sh
# Migrate, ingest the record (incremental, skips unchanged chunks), then serve.
set -eu
alembic upgrade head
me-agent ingest
exec uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*' "$@"
