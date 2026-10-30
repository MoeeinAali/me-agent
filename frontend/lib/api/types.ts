// Mirrors backend/app/domain.py (exported as data/api.schema.json). Validated at runtime with
// zod so a backend change surfaces as a clear error instead of a broken screen.
import { z } from "zod";

export const Capability = z.enum([
  "answer_from_record",
  "answer_from_api",
  "clarify",
  "refuse_unpublished",
  "refuse_action",
  "out_of_scope",
]);
export const Intent = z.enum([
  "project_summary",
  "reading_suggestion",
  "job_fit",
  "fact_lookup",
  "out_of_scope",
  "smalltalk",
]);
export const Audience = z.enum(["recruiter", "tech_lead", "professor", "general"]);
export const Lang = z.enum(["fa", "en"]);

export const Proof = z.object({
  type: z.enum(["record", "github_repo", "github_commit", "live_url", "syllabus"]),
  url: z.string().nullable().optional(),
  status: z.enum(["up", "down", "unknown"]).nullable().optional(),
  checked_at: z.string().nullable().optional(),
});

export const Evidence = z.object({
  id: z.string(),
  path: z.string(),
  value: z.string(),
  source: z.enum(["record", "github", "hrcando", "job_text", "link_check"]),
  trusted: z.boolean(),
  proof: Proof,
});

export const Claim = z.object({ text: z.string(), evidence: z.array(z.string()) });

export const ToolCall = z.object({
  name: z.string(),
  ok: z.boolean(),
  latency_ms: z.number(),
  detail: z.string().nullable().optional(),
});

export const ScorecardRow = z.object({
  requirement: z.string(),
  category: z.enum(["must", "nice"]),
  kind: z.enum(["skill", "experience", "education", "language", "other"]),
  status: z.enum(["matched", "partial", "no_evidence"]),
  evidence: z.array(z.string()),
});

export const Scorecard = z.object({
  job: z.object({
    source: z.string(),
    url: z.string().nullable().optional(),
    company: z.string().nullable().optional(),
    title: z.string().nullable().optional(),
  }),
  rows: z.array(ScorecardRow),
  coverage: z.number(),
  verdict: z.enum(["strong", "partial", "weak"]),
});

export const Trace = z.object({
  id: z.string(),
  question: z.string(),
  language: Lang,
  intent: Intent,
  audience: Audience,
  channel: z.string(),
  fields_read: z.array(z.string()),
  tools_called: z.array(ToolCall),
  capability: Capability,
  answer: z.string(),
  missing: z.array(z.string()),
  latency_ms: z.number(),
  tokens_in: z.number(),
  tokens_out: z.number(),
  prompt_version: z.string(),
});

export const ChatResponse = z.object({
  conversation_id: z.string(),
  answer: z.string(),
  capability: Capability,
  claims: z.array(Claim),
  evidence: z.array(Evidence),
  scorecard: Scorecard.nullable().optional(),
  clarify_options: z.array(z.string()).nullable().optional(),
  transcript: z.string().nullable().optional(),
  audio_b64: z.string().nullable().optional(),
  trace: Trace,
});

export const Limits = z.object({
  forbidden_actions: z.array(z.string()),
  unpublished_topics: z.array(z.string()),
  guardrails: z.array(z.string()),
});

export type Capability = z.infer<typeof Capability>;
export type Audience = z.infer<typeof Audience>;
export type Lang = z.infer<typeof Lang>;
export type Evidence = z.infer<typeof Evidence>;
export type Claim = z.infer<typeof Claim>;
export type Scorecard = z.infer<typeof Scorecard>;
export type ChatResponse = z.infer<typeof ChatResponse>;
export type Limits = z.infer<typeof Limits>;

export type ChatRequest = {
  message: string;
  audience: Audience;
  conversation_id?: string;
  job_url?: string;
  job_text?: string;
};
