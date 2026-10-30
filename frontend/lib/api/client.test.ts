import { afterEach, describe, expect, it, vi } from "vitest";

import { fixtureResponse } from "@/test/fixtures";
import { type StreamEvent, streamChat } from "./client";

function sseResponse(body: string): Response {
  return new Response(body, {
    status: 200,
    headers: { "content-type": "text/event-stream" },
  });
}

afterEach(() => vi.unstubAllGlobals());

describe("streamChat", () => {
  it("emits typed events and validates the final response", async () => {
    const final = fixtureResponse({ answer: "Hi" });
    vi.stubGlobal("fetch", vi.fn(async () =>
      sseResponse(`event: token\ndata: {"text":"Hi"}\n\nevent: final\ndata: ${JSON.stringify(final)}\n\n`),
    ));
    const events: StreamEvent[] = [];
    await streamChat({ message: "q", audience: "general" }, (e) => events.push(e));
    expect(events.map((e) => e.type)).toEqual(["token", "final"]);
  });

  it("invalid final payload becomes an error event", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => sseResponse('event: final\ndata: {"nope":1}\n\n')));
    const events: StreamEvent[] = [];
    await streamChat({ message: "q", audience: "general" }, (e) => events.push(e));
    expect(events).toEqual([{ type: "error", message: "The server sent an unexpected response." }]);
  });

  it("HTTP errors surface the server's detail", async () => {
    vi.stubGlobal("fetch", vi.fn(async () =>
      new Response(JSON.stringify({ detail: "Too many requests." }), { status: 429 }),
    ));
    await expect(streamChat({ message: "q", audience: "general" }, () => {})).rejects.toThrow(
      "Too many requests.",
    );
  });
});
