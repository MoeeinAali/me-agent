# HW1 — A personal AI-native page (Moeein Aali)

> **Status (2026-10-30):** deployed to the personal k3s cluster (manifests in `me-infra/apps/me-agent`). The
> API shares the cluster Postgres (pgvector added). The three traces were
> taken from the local stack with the real model (GapGPT). **Re-take them from the live page after
> deploying** (`uv run me-agent traces --capability … --limit 1`).

## 1. Public address and deploy steps

- Public address: **https://agent.moeein.me** (API: https://agent-api.moeein.me)
- Images: `ghcr.io/<owner>/me-agent-api` and `ghcr.io/<owner>/me-agent-web`, built by
  `.github/workflows/images.yml` on every push to `main`
- Run locally: `cp .env.example .env` (set `LLM_API_KEY`), then `docker compose up --build`.
  The API is on `:8000` and the web app on `:3000`.
- At container start the API runs `alembic upgrade head`, then `me-agent ingest`, then `uvicorn`.

## 2. The record (JSON) and which fields are visible

- **Filled record:** `data/record.json`. It was built from the personal site (`me-frontend`) and
  the LaTeX CV by `app/importer/build_record.py`, and site/CV conflicts were reviewed in
  `data/conflicts.md`.
- **Schema:** `data/record.schema.json`, exported from the Pydantic models in
  `backend/app/record/schema.py`.
- **Visibility:** every property carries `x-visibility`. All personal fields are `public` (Moeein's
  decision: everything on his site and CV is public). Import bookkeeping (`meta.sources`) is
  `internal`, and `GET /v1/record` returns only public fields.
- **Contents:** courses (`courses_taken`, plus `data/syllabus.json` with **topics only** for
  the courses he took), projects, experience, teaching, service, skills, books, FAQ, and
  **limits**.

## 3. Capabilities and authority

The model can only end in one of these actions, and code (not the model) chooses which:

| Capability | When |
|---|---|
| `answer_from_record` | every claim cites trusted evidence from the record |
| `answer_from_api` | a claim relies on GitHub, a live-link check, or an hrcando job posting |
| `clarify` | the question is ambiguous (e.g. "his project" with 16 projects), or a job is needed |
| `refuse_unpublished` | the fact is not in the record, or is a topic Moeein chose not to publish |
| `refuse_action` | asked to email, book a meeting, apply to a job, speak for Sharif, or contact anyone |
| `out_of_scope` | not about Moeein |

The limits (forbidden actions, unpublished topics, guardrails) live in `record.limits`. They're
served by `GET /v1/limits` for the page and rendered into the system prompt, so the page and the
model see the same list.

## 4. Other apps and APIs used

- **GapGPT** (OpenAI-compatible): understanding, answering, embeddings (`text-embedding-3-small`),
  speech-to-text and text-to-speech
- **GitHub REST API:** live repo facts (languages, last push, latest commit) for projects in the
  record
- **hrcando career API:** job postings from `career.hrcando.ir/co/<company>/job-detail/<uuid>`
  links, used for the job-fit scorecard
- **Live link check:** whether each project's site is up right now (the "verifiable CV" proof)

## 5. Explainability

Every answer returns a trace: the intent, the **fields read** (record paths such as
`projects[comeback].summary`), the tools called, the **capability**, and the **missing facts**.
It also returns each claim with the evidence IDs it cites and a proof link (GitHub, live URL,
syllabus page, or record path).

## 6. Creativity

- **Job-fit scorecard plus verifiable CV:** requirement-by-requirement matched / partial / no
  evidence, with proofs, and coverage and verdict computed in code.
- Answers tailored to the audience (recruiter, tech lead, professor), live-trace streaming (SSE),
  voice in and out, an MCP server so other AI assistants can ask about Moeein, and a
  knowledge-gap loop (`me-agent gaps`).

## 7. Three traces

### 7.1 Good answer

```
Question: پروژه کامبک رو خلاصه کن
Intent: project_summary
Fields read: projects[comeback].summary, projects[comeback].role, projects[comeback].tech,
             projects[comeback].highlights[0..10], projects[comeback].body[overview],
             projects[comeback].body[product-engineering], …, projects[comeback].links.live,
             projects[comeback].links.marketplace, experience[yektanet-software-engineer-comeback].bullets[0]
Capability: answer_from_api
Tools: link_check:https://comeback.top/ (ok), link_check:https://cafebazaar.ir/app/top.comeback.twa (ok)
Answer: پروژه کامبک یک پلتفرم ورزشی فارسی بهینه‌سازی‌شده و شبیه اپلیکیشن بومی است که از ابتدا
        ساخته شده و به بیش از یک میلیون کاربر خدمت‌رسانی کرده است. … فرانت‌اند با Next.js ساخته
        شده و سرویس‌های Go پشتیبان نیازهای بک‌اند هستند. … تحویل روی Kubernetes با Bazel …
        نقش معین در این پروژه، مهندس نرم‌افزار در یکتانت بوده است. آدرس پروژه: https://comeback.top/
```
Trace id `6c30f4f2-9b90-457b-a1af-2657d41a31b7`.

### 7.2 Refusal (a fact that is not in the record)

```
Question: Did he work at Google?
Intent: fact_lookup
Fields read: experience[yektanet-software-engineer-comeback].bullets[2], experience[yektanet-front-end-engineer].tech,
             experience[zerang-former-co-founder-software-engineer].summary, … (10 fields, none mention Google)
Capability: refuse_unpublished
Missing: employment at Google
Answer: That isn't in Moeein's published record, so I can't answer it. Not in the record: employment at Google.
```
Trace id `6ef49a2a-85d7-4279-b8b1-69111e04772b`. The question was also saved as a knowledge gap.

### 7.3 Clarifying question

```
Question: Tell me about his project
Intent: project_summary
Fields read: (none)
Capability: clarify
Answer: Which project do you mean: Arcadia, ASIS Badges, Byte Publication Website, Comeback,
        Creepy Gopher, Kanban Board, L.A. Noire or LakLak?
```
Trace id `1d245232-4c56-4c44-9696-2958aa8befa5`. The current build lists featured projects first
and says "For example: …" when the list is truncated.
