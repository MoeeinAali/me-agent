import { describe, expect, it } from "vitest";

import { parseSSE } from "./sse";

describe("parseSSE", () => {
  it("parses events split across chunks", () => {
    const raw = 'event: final\r\ndata: {"answer":"hi"}\r\n\r\n';
    let rest = "";
    const all = [];
    for (const piece of [raw.slice(0, 7), raw.slice(7, 30), raw.slice(30)]) {
      const out = parseSSE(piece, rest);
      all.push(...out.events);
      rest = out.rest;
    }
    expect(all).toEqual([{ event: "final", data: '{"answer":"hi"}' }]);
    expect(rest).toBe("");
  });

  it("parses several events in one chunk and ignores comments", () => {
    const raw = ": ping\n\nevent: token\ndata: {\"text\":\"a\"}\n\nevent: token\ndata: {\"text\":\"b\"}\n\n";
    expect(parseSSE(raw, "").events.map((e) => e.data)).toEqual(['{"text":"a"}', '{"text":"b"}']);
  });

  it("joins multi-line data", () => {
    expect(parseSSE("event: x\ndata: a\ndata: b\n\n", "").events[0].data).toBe("a\nb");
  });
});
