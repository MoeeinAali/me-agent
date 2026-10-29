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
