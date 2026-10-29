#!/bin/sh
# Migrate, ingest the record (incremental, skips unchanged chunks), then serve.
# Client IPs (used for rate limiting) are read from X-Forwarded-For only when the request comes
# from FORWARDED_ALLOW_IPS — set it to the reverse proxy's address/CIDR in deployment.
set -eu
alembic upgrade head
me-agent ingest
exec uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --proxy-headers \
  --forwarded-allow-ips="${FORWARDED_ALLOW_IPS:-127.0.0.1}" "$@"
