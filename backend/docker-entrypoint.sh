#!/bin/sh
# Migrate, ingest the record (incremental, skips unchanged chunks), then serve.
# A failed ingest (e.g. the embedding API is down) must not stop the API: the previous index is
# still in the database, and the next start retries.
# Client IPs (used for rate limiting) are read from X-Forwarded-For only when the request comes
# from FORWARDED_ALLOW_IPS — set it to the reverse proxy's address/CIDR in deployment.
set -eu
alembic upgrade head
me-agent ingest || echo "warning: ingest failed; serving the existing index" >&2
exec uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --proxy-headers \
  --forwarded-allow-ips="${FORWARDED_ALLOW_IPS:-127.0.0.1}" "$@"
