import { describe, expect, it } from "vitest";

import { fixtureResponse } from "@/test/fixtures";
import type { StreamEvent } from "./api/client";
import { createChatStore } from "./store";

function fakeStream(events: StreamEvent[], fail?: Error) {
  return async (_req: unknown, onEvent: (e: StreamEvent) => void) => {
    for (const e of events) onEvent(e);
    if (fail) throw fail;
  };
}

describe("chat store", () => {
  it("applies stages, tokens, then final", async () => {
    const final = fixtureResponse({ answer: "Hello world" });
    const store = createChatStore(
      fakeStream([
        { type: "stage", name: "understand", status: "start" },
        { type: "stage", name: "understand", status: "done" },
        { type: "token", text: "Hello " },
        { type: "token", text: "world" },
        { type: "final", data: final },
      ]),
    );
    await store.getState().send("hi");
    const [user, assistant] = store.getState().messages;
    expect(user).toMatchObject({ role: "user", text: "hi" });
    expect(assistant.text).toBe("Hello world");
    expect(assistant.status).toBe("done");
    expect(assistant.stages.understand).toBe("done");
    expect(assistant.response?.capability).toBe(final.capability);
    expect(store.getState().conversationId).toBe(final.conversation_id);
  });

  it("stream error sets status error and keeps partial text", async () => {
    const store = createChatStore(
      fakeStream([{ type: "token", text: "Part" }], new Error("network down")),
    );
    await store.getState().send("hi");
    const assistant = store.getState().messages[1];
    expect(assistant.status).toBe("error");
    expect(assistant.text).toBe("Part");
    expect(assistant.error).toMatch(/network/i);
  });

  it("server error event becomes an error state", async () => {
    const store = createChatStore(fakeStream([{ type: "error", message: "Please retry." }]));
    await store.getState().send("hi");
    expect(store.getState().messages[1]).toMatchObject({ status: "error", error: "Please retry." });
  });

  it("retry resends the user's question", async () => {
    let calls = 0;
    const store = createChatStore(async (_req, onEvent) => {
      calls += 1;
      if (calls === 1) throw new Error("boom");
      onEvent({ type: "final", data: fixtureResponse({ answer: "ok" }) });
    });
    await store.getState().send("question");
    const failed = store.getState().messages[1];
    await store.getState().retry(failed.id);
    const messages = store.getState().messages;
    expect(messages).toHaveLength(2);
    expect(messages[1]).toMatchObject({ status: "done", text: "ok" });
  });

  it("sends the selected audience and conversation id", async () => {
    const seen: unknown[] = [];
    const store = createChatStore(async (req, onEvent) => {
      seen.push(req);
      onEvent({ type: "final", data: fixtureResponse({ answer: "a" }) });
    });
    store.getState().setAudience("professor");
    await store.getState().send("one");
    await store.getState().send("two");
    expect(seen[0]).toMatchObject({ message: "one", audience: "professor" });
    expect(seen[1]).toMatchObject({ conversation_id: fixtureResponse({}).conversation_id });
  });
});
