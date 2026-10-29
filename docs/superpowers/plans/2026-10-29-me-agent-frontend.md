# me-agent Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A single-page Next.js app where a visitor asks questions about Moeein and sees the answer, why it was given (a live trace and proofs), the job-fit scorecard, and the page's limits.

**Architecture:**
- A thin client over the backend API (`NEXT_PUBLIC_API_BASE_URL`). It holds no knowledge and makes no LLM calls.
- The state is one conversation in a Zustand store, fed by SSE events from `/v1/chat/stream`.
- The theme is copied from `../me-frontend`.

**Tech Stack:** Next.js 16 (App Router, `output: "standalone"`), React 19, TypeScript, Tailwind v4, shadcn/ui (`base-lyra`, zinc), lucide-react, motion, Zustand, Zod, Vitest + Testing Library, pnpm.

**Spec:** `docs/superpowers/specs/2026-10-29-me-agent-design.md` §18. **API contract:** backend plan Task 5 (`data/api.schema.json`).

## Global Constraints

- Copy the tokens from `../me-frontend/app/globals.css`, unchanged:
  - primary `oklch(0.852 0.199 91.936)` (light) / `oklch(0.795 0.184 86.047)` (dark), and `--radius: 0.625rem`
  - fonts: Geist (sans) and JetBrains Mono (mono + headings)
  - `<html className="dark">` by default
- Persian text uses **Vazirmatn**. Every message bubble and claim has `dir="auto"`. The page itself stays LTR.
- Capability badge labels (en / fa):
  - `answer_from_record` = "From record" / «از رکورد»
  - `answer_from_api` = "From API" / «از API»
  - `clarify` = "Needs clarification" / «نیاز به توضیح»
  - `refuse_unpublished` = "Not published" / «منتشر نشده»
  - `refuse_action` = "Not allowed" / «مجاز نیست»
  - `out_of_scope` = "Outside this page" / «خارج از این صفحه»
- The page shows, under the input: "Answers come only from Moeein's record, GitHub, and job pages you share. Powered by GapGPT." (Persian variant when the UI language is fa).
- Never render the answer from anything but `token`/`final` events. There is no client-side text generation.
- Commits end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **The SSE stream drops mid-answer** (network or 5xx): the message must show an error state with a retry, not a stuck spinner. Tested in Task 2.
2. **A long Persian answer containing English tech names** must render RTL correctly, with no reversed punctuation in mixed runs. Tested in Task 3 (snapshot with `dir="auto"`).
3. **A clarify response** must render its options as buttons that send the chosen label as the next message. Tested in Task 3.
4. **Microphone permission denied, or the browser has no MediaRecorder:** the mic button is disabled with a tooltip, and nothing crashes. Tested in Task 6.
5. **Phone width (360px):** the trace panel stacks under the message, and there's no horizontal scroll from the scorecard table, which scrolls inside its own container. Covered by the Task 7 manual check.

---

### Task 1: Scaffold + theme

**Files:**
- Create: `frontend/` via `pnpm create next-app@16 frontend --ts --tailwind --app --eslint --no-src-dir --import-alias "@/*"`, `frontend/components.json` (copied from me-frontend, `rsc: true`), `frontend/app/globals.css`, `frontend/app/layout.tsx`, `frontend/lib/utils.ts`, `frontend/vitest.config.ts`, `frontend/.env.example`

- [ ] **Step 1:** Scaffold. Copy `globals.css`'s theme blocks (`@theme inline`, `:root`, `.dark`) from `../me-frontend/app/globals.css`, and the `Geist` / `JetBrains_Mono` setup from `../me-frontend/app/layout.tsx`. Add `Vazirmatn` via `next/font/google` (subsets `arabic`) as `--font-fa`, with a `:lang(fa), [dir=rtl]` rule using it. Set `next.config.ts` to `output: "standalone"`.
- [ ] **Step 2:** `pnpm dlx shadcn@latest add button textarea card badge sheet tabs tooltip scroll-area table select collapsible sonner skeleton`.
- [ ] **Step 3:** Add `package.json` scripts `lint`, `typecheck` (`tsc --noEmit`), and `test` (`vitest run`).
- [ ] **Step 4:** `pnpm lint && pnpm typecheck && pnpm build` succeeds. `pnpm dev` shows a dark page with the yellow primary button.
- [ ] **Step 5:** Commit with `feat(web): scaffold Next.js app with me-frontend theme`.

---

### Task 2: API types, client, SSE parser, store

**Files:**
- Create: `frontend/lib/api/types.ts`, `frontend/lib/api/client.ts`, `frontend/lib/api/sse.ts`, `frontend/lib/store.ts`, `frontend/lib/api/sse.test.ts`, `frontend/lib/store.test.ts`

**Interfaces:**
- Produces:
  - Zod schemas mirroring backend Task 5: `ChatResponse`, `Evidence`, `Claim`, `Trace`, `Scorecard`, `Capability`, `Audience`.
  - `parseSSE(chunk: string, buffer: string): { events: SSEEvent[]; rest: string }`, with `SSEEvent = {type:"stage",name,status} | {type:"evidence",data:Evidence} | {type:"token",text} | {type:"final",data:ChatResponse} | {type:"error",message}`.
  - `streamChat(req: ChatRequest, onEvent: (e: SSEEvent) => void, signal?: AbortSignal): Promise<void>` (a fetch + ReadableStream reader on `/v1/chat/stream`).
  - `postJobFit(form: FormData)`, `postVoice(form: FormData)`, `getLimits()`, `getSuggestions(audience, lang)`.
  - The store `useChat` holds:
    - `conversationId`, `audience`, `messages: UIMessage[]`
    - `UIMessage = {id, role:"user"|"assistant", text, status:"streaming"|"done"|"error", stages: Record<string,"start"|"done">, evidence: Evidence[], response?: ChatResponse, error?: string}`

    Actions: `send(text, extras?)`, `retry(id)`, `setAudience`.

- [ ] **Step 1: Write failing tests:**
  - `parses events split across chunks` (one `final` event split over 3 chunks yields 1 event).
  - `store applies token then final` (the text equals the concatenated tokens, then status `done` and `response` is set).
  - `stream error sets status error and keeps partial text`.
  - `final event validated with zod; invalid final → error state`.
- [ ] **Step 2:** Run `pnpm test` and expect FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run `pnpm test` and expect PASS.
- [ ] **Step 5:** Commit with `feat(web): typed API client, SSE parser, chat store`.

---

### Task 3: Chat UI (messages, input, clarify, capability badges)

**Files:**
- Create: `frontend/app/page.tsx`, `frontend/components/chat/MessageList.tsx`, `frontend/components/chat/MessageBubble.tsx`, `frontend/components/chat/Composer.tsx`, `frontend/components/chat/CapabilityBadge.tsx`, `frontend/components/chat/ClarifyOptions.tsx`, `frontend/components/chat/Suggestions.tsx`, `frontend/components/chat/*.test.tsx`

- [ ] **Step 1: Write failing tests:**
  - `MessageBubble renders dir=auto and capability badge label`: the `refuse_unpublished` badge reads "Not published".
  - `ClarifyOptions click sends label`: clicking the "Comeback" option calls `send("Comeback")`.
  - `Composer submits on Enter, newline on Shift+Enter, disabled while streaming, max 2000 chars counter`.
  - `Suggestions shown only when no messages`.
- [ ] **Step 2:** Run them and expect FAIL.
- [ ] **Step 3:** Implement. The layout has a header (name, headline, audience `Select`), a scrollable message list, and a composer pinned at the bottom. Refusal and clarify bubbles use a muted border and an icon, so they're visually distinct from answers.
- [ ] **Step 4:** Run them and expect PASS. Manually, against a running backend, a Persian question streams.
- [ ] **Step 5:** Commit with `feat(web): chat UI with clarify and capability badges`.

---

### Task 4: "Why this answer" panel + claim proofs

**Files:**
- Create: `frontend/components/trace/TracePanel.tsx`, `frontend/components/trace/StageProgress.tsx`, `frontend/components/trace/ProofChip.tsx`, `frontend/components/trace/ClaimList.tsx`, `frontend/components/trace/*.test.tsx`

- [ ] **Step 1: Write failing tests:**
  - `StageProgress shows six stages with live status`.
  - `TracePanel lists intent, capability, fields_read paths (mono font), tools_called with ok/failed, and missing facts` (from a fixture ChatResponse).
  - `ProofChip renders github link, live_url with up/down + relative checked_at, syllabus label, record path`.
  - `ClaimList maps claim.evidence ids to chips; unknown id not rendered`.
- [ ] **Step 2:** Run them and expect FAIL.
- [ ] **Step 3:** Implement as a `Collapsible` under each assistant bubble, open while streaming and collapsed when done.
- [ ] **Step 4:** Run them and expect PASS.
- [ ] **Step 5:** Commit with `feat(web): explainability panel and verifiable claim proofs`.

---

### Task 5: Job input + scorecard view

**Files:**
- Create: `frontend/components/job/JobAttach.tsx`, `frontend/components/job/Scorecard.tsx`, `frontend/components/job/*.test.tsx`

- [ ] **Step 1: Write failing tests:**
  - `JobAttach tabs: URL | Paste text | PDF; PDF > 2MB shows error without request`.
  - `Scorecard renders coverage %, verdict band, rows with ✅/🟡/❌ and must/nice, evidence chips; table wrapped in horizontal ScrollArea`.
- [ ] **Step 2:** Run them and expect FAIL.
- [ ] **Step 3:** Implement. JobAttach opens from the composer's paperclip button. A URL or text goes through `streamChat` with `job_url` / `job_text`, and a PDF goes to `postJobFit`. The scorecard renders inside the assistant bubble when `response.scorecard` is present.
- [ ] **Step 4:** Run them and expect PASS.
- [ ] **Step 5:** Commit with `feat(web): job attach and fit scorecard`.

---

### Task 6: Limits panel, voice, footer notice

**Files:**
- Create: `frontend/components/LimitsSheet.tsx`, `frontend/components/voice/MicButton.tsx`, `frontend/components/voice/*.test.tsx`, `frontend/components/LimitsSheet.test.tsx`

- [ ] **Step 1: Write failing tests:**
  - `LimitsSheet renders forbidden_actions, unpublished_topics, guardrails from getLimits fixture`.
  - `MicButton disabled with tooltip when MediaRecorder undefined`.
  - `MicButton permission denied → toast, no throw`.
  - `MicButton stops at 60s and posts FormData with audio + audience + conversation_id`.
- [ ] **Step 2:** Run them and expect FAIL.
- [ ] **Step 3:** Implement. The limits are reachable from a header button ("What I can't do" / «محدودیت‌ها»). A "speak answer" toggle sends `tts=true`, and the `audio_b64` is played with an `<audio>` element. The footer notice text comes from Global Constraints.
- [ ] **Step 4:** Run them and expect PASS.
- [ ] **Step 5:** Commit with `feat(web): limits panel, voice input/output`.

---

### Task 7: Docker image, compose, CI

**Files:**
- Create: `frontend/Dockerfile`, `frontend/.dockerignore`
- Modify: `compose.yaml` (add `web`, `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`, depends_on `api`), `.github/workflows/ci.yml` (add a `frontend` job: pnpm install --frozen-lockfile, lint, typecheck, test, build), `.github/workflows/images.yml` (add the matrix entry `{name: web, context: frontend, file: frontend/Dockerfile}` with build-arg `NEXT_PUBLIC_API_BASE_URL`)

- [ ] **Step 1:** Write the multi-stage Dockerfile (`node:24-alpine`, corepack pnpm, standalone output, non-root `nextjs` user, port 3000).
- [ ] **Step 2:** `docker compose up --build`. At `http://localhost:3000`, ask the three HW questions and see an answer, a refusal, and a clarify, each with its trace panel.
- [ ] **Step 3:** Manual check at 360px width in devtools: no horizontal page scroll, and the trace panel is stacked.
- [ ] **Step 4:** actionlint is clean.
- [ ] **Step 5:** Commit with `ci: web image, compose web, frontend CI`.
