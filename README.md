# me-agent

A grounded, explainable AI that stands in for Moeein Aali in interviews. Every fact it states comes
from `data/record.json` or an external API it called, and every answer ships with its trace.

- `backend/` — FastAPI agent (Postgres + pgvector, GapGPT via an OpenAI-compatible client)
- `frontend/` — Next.js UI
- `data/` — the record (source of truth), its JSON Schema, and the Sharif CE syllabus topics
- `evals/` — evaluation cases
- `docs/` — design spec, plans, report

## Quick start

```bash
cp .env.example .env          # set LLM_API_KEY
docker compose up --build     # db + api (:8000) + web (:3000)
```

## Deploy

Step-by-step for Hamravesh (Darkube) and the personal k3s cluster: [`DEPLOY.md`](DEPLOY.md).

| Variable | Where | What |
|---|---|---|
| `DATABASE_URL` | api | `postgresql+asyncpg://user:pass@host:5432/db`; the role must be able to `CREATE EXTENSION vector` |
| `LLM_API_KEY` | api | GapGPT key (secret) |
| `CORS_ORIGINS` | api | JSON list of web origins, e.g. `["https://agent.example"]` |
| `RATE_LIMIT_CLIENT_HEADER` | api | Header with the visitor IP behind a proxy/CDN (`x-real-ip` on Darkube, `cf-connecting-ip` behind Cloudflare) |
| `RATE_LIMIT_TRUSTED_PROXIES` | api | JSON list of CIDRs allowed to set that header (the ingress or CDN); from anyone else it is ignored |
| `API_BASE_URL` | web | Public API address the browser calls; read at runtime |

## Use it from an AI assistant (MCP)

The API serves an MCP endpoint (streamable HTTP) at `/mcp/` with four tools:
`ask_about_moeein`, `job_fit`, `list_projects`, `get_limits`. Every tool runs the same grounded
pipeline and returns the evidence and trace.

Claude Code: `claude mcp add --transport http me-agent http://localhost:8000/mcp/`

Claude Desktop (`claude_desktop_config.json`):

```json
{ "mcpServers": { "me-agent": { "command": "npx", "args": ["mcp-remote", "http://localhost:8000/mcp/"] } } }
```

## Knowledge gaps

```bash
cd backend
uv run me-agent gaps                                   # open gaps, most-asked first
uv run me-agent gaps answer 42 "Yes, remote or hybrid." --question "Is Moeein open to remote work?"
uv run me-agent gaps ignore 43
uv run me-agent eval --subset smoke                    # eval suite against the real model
```
