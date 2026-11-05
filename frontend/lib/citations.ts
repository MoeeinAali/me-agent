import type { ChatResponse, Claim, Evidence } from "./api/types";

export type Source = Evidence & { n: number };
export type Segment =
  | { kind: "text"; text: string }
  | { kind: "claim"; text: string; bullet: boolean; sources: Source[] };

/** Number the cited, existing evidence in order of first citation: [1], [2], … */
export function numberSources(response: ChatResponse): Source[] {
  const byId = new Map(response.evidence.map((e) => [e.id, e]));
  const sources: Source[] = [];
  const seen = new Set<string>();
  for (const claim of response.claims) {
    for (const id of claim.evidence) {
      const item = byId.get(id);
      if (item && !seen.has(id)) {
        seen.add(id);
        sources.push({ ...item, n: sources.length + 1 });
      }
    }
  }
  return sources;
}

/** Mirrors backend compose_answer: claims joined by a space, or a newline around bullets. */
function joinClaims(claims: Claim[]): string {
  let body = "";
  let previous: string | null = null;
  for (const claim of claims) {
    const text = claim.text.trim();
    if (previous !== null) body += text.startsWith("- ") || previous.startsWith("- ") ? "\n" : " ";
    body += text;
    previous = text;
  }
  return body;
}

/**
 * Split the answer into its verified claims (each with its numbered sources) and the fixed text
 * around them (a job-fit summary before, a "not in the record" note after). Falls back to the plain
 * answer when the claims can't be located in it.
 */
export function segmentAnswer(response: ChatResponse, sources: Source[]): Segment[] {
  const claims = response.claims.filter((c) => c.text.trim());
  const joined = joinClaims(claims);
  const at = joined ? response.answer.indexOf(joined) : -1;
  if (at < 0) return [{ kind: "text", text: response.answer }];
  const byId = new Map(sources.map((s) => [s.id, s]));
  const segments: Segment[] = [];
  const before = response.answer.slice(0, at).trim();
  const after = response.answer.slice(at + joined.length).trim();
  if (before) segments.push({ kind: "text", text: before });
  for (const claim of claims) {
    const text = claim.text.trim();
    const bullet = text.startsWith("- ");
    segments.push({
      kind: "claim",
      text: bullet ? text.slice(2) : text,
      bullet,
      sources: claim.evidence.map((id) => byId.get(id)).filter((s): s is Source => !!s),
    });
  }
  if (after) segments.push({ kind: "text", text: after });
  return segments;
}
