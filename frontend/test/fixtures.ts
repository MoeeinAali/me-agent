import type { ChatResponse } from "@/lib/api/types";

export function fixtureResponse(overrides: Partial<ChatResponse>): ChatResponse {
  const answer = overrides.answer ?? "Comeback is a Persian sports PWA.";
  return {
    conversation_id: "6b7a1f6e-1c2d-4e5f-8a9b-0c1d2e3f4a5b",
    answer,
    capability: "answer_from_record",
    claims: [{ text: answer, evidence: ["E1"] }],
    evidence: [
      {
        id: "E1",
        path: "projects[comeback].summary",
        value: "Comeback — A Persian sports PWA.",
        source: "record",
        trusted: true,
        proof: { type: "record", url: null, status: null, checked_at: null },
      },
    ],
    scorecard: null,
    clarify_options: null,
    transcript: null,
    audio_b64: null,
    trace: {
      id: "11111111-2222-3333-4444-555555555555",
      question: "Summarize Comeback",
      language: "en",
      intent: "project_summary",
      audience: "general",
      channel: "sse",
      fields_read: ["projects[comeback].summary"],
      tools_called: [],
      capability: "answer_from_record",
      answer,
      missing: [],
      latency_ms: 1200,
      tokens_in: 100,
      tokens_out: 20,
      prompt_version: "abcd1234",
    },
    ...overrides,
  };
}
