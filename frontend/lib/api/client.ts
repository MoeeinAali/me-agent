import { parseSSE } from "./sse";
import {
  type Audience,
  ChatResponse,
  type ChatRequest,
  Evidence,
  type Lang,
  Limits,
} from "./types";

export const API_BASE = (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000").replace(
  /\/$/,
  "",
);

export type StageName = "understand" | "resolve" | "policy" | "evidence" | "generate" | "verify";
export type StreamEvent =
  | { type: "stage"; name: StageName; status: "start" | "done" }
  | { type: "evidence"; data: Evidence }
  | { type: "token"; text: string }
  | { type: "final"; data: ChatResponse }
  | { type: "error"; message: string };

const UNEXPECTED = "The server sent an unexpected response.";

async function errorDetail(response: Response): Promise<string> {
  try {
    const body = await response.json();
    if (typeof body?.detail === "string") return body.detail;
  } catch {
    // fall through
  }
  return `Request failed (HTTP ${response.status}).`;
}

function toEvent(event: string, data: string): StreamEvent {
  try {
    const payload = JSON.parse(data);
    switch (event) {
      case "stage":
        return { type: "stage", name: payload.name, status: payload.status };
      case "evidence": {
        const parsed = Evidence.safeParse(payload);
        return parsed.success ? { type: "evidence", data: parsed.data } : { type: "error", message: UNEXPECTED };
      }
      case "token":
        return { type: "token", text: String(payload.text ?? "") };
      case "final": {
        const parsed = ChatResponse.safeParse(payload);
        return parsed.success ? { type: "final", data: parsed.data } : { type: "error", message: UNEXPECTED };
      }
      case "error":
        return { type: "error", message: String(payload.message ?? UNEXPECTED) };
    }
  } catch {
    // fall through
  }
  return { type: "error", message: UNEXPECTED };
}

/** POST /v1/chat/stream and emit typed events until the stream ends. */
export async function streamChat(
  req: ChatRequest,
  onEvent: (event: StreamEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const response = await fetch(`${API_BASE}/v1/chat/stream`, {
    method: "POST",
    headers: { "content-type": "application/json", accept: "text/event-stream" },
    body: JSON.stringify(req),
    signal,
  });
  if (!response.ok || !response.body) throw new Error(await errorDetail(response));
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let rest = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    const parsed = parseSSE(decoder.decode(value, { stream: true }), rest);
    rest = parsed.rest;
    for (const raw of parsed.events) onEvent(toEvent(raw.event, raw.data));
  }
}

async function postForm(path: string, form: FormData): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE}${path}`, { method: "POST", body: form });
  if (!response.ok) throw new Error(await errorDetail(response));
  const parsed = ChatResponse.safeParse(await response.json());
  if (!parsed.success) throw new Error(UNEXPECTED);
  return parsed.data;
}

export const postJobFit = (form: FormData) => postForm("/v1/jobs/fit", form);
export const postVoice = (form: FormData) => postForm("/v1/voice", form);

export async function getLimits(): Promise<Limits> {
  const response = await fetch(`${API_BASE}/v1/limits`);
  if (!response.ok) throw new Error(await errorDetail(response));
  return Limits.parse(await response.json());
}

export async function getSuggestions(audience: Audience, lang: Lang): Promise<string[]> {
  const response = await fetch(`${API_BASE}/v1/suggestions?audience=${audience}&lang=${lang}`);
  if (!response.ok) return [];
  const body = await response.json();
  return Array.isArray(body?.suggestions) ? body.suggestions.map(String) : [];
}
