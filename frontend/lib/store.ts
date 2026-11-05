import { createStore } from "zustand/vanilla";

import { type StageName, type StreamEvent, streamChat } from "./api/client";
import type { Audience, ChatRequest, ChatResponse, Evidence } from "./api/types";

export type UIMessage = {
  id: string;
  role: "user" | "assistant";
  text: string;
  status: "streaming" | "done" | "error";
  stages: Partial<Record<StageName, "start" | "done">>;
  evidence: Evidence[];
  response?: ChatResponse;
  error?: string;
  request?: Omit<ChatRequest, "audience" | "conversation_id">;
};

export type ChatState = {
  conversationId?: string;
  audience: Audience;
  messages: UIMessage[];
  busy: boolean;
  /** The assistant message whose sources the inspector shows. */
  selectedId?: string;
  select: (id: string | undefined) => void;
  reset: () => void;
  send: (text: string, extras?: { job_url?: string; job_text?: string }) => Promise<void>;
  /** Add a finished exchange produced outside the stream (job PDF upload, voice). */
  addExchange: (question: string, response: ChatResponse) => void;
  retry: (assistantId: string) => Promise<void>;
  setAudience: (audience: Audience) => void;
};

type StreamFn = (
  req: ChatRequest,
  onEvent: (event: StreamEvent) => void,
  signal?: AbortSignal,
) => Promise<void>;

const id = () => (globalThis.crypto?.randomUUID?.() ?? Math.random().toString(36).slice(2));

export function createChatStore(stream: StreamFn = streamChat) {
  return createStore<ChatState>()((set, get) => {
    const patch = (messageId: string, update: (m: UIMessage) => Partial<UIMessage>) =>
      set((state) => ({
        messages: state.messages.map((m) => (m.id === messageId ? { ...m, ...update(m) } : m)),
      }));

    const run = async (assistantId: string, request: NonNullable<UIMessage["request"]>) => {
      set({ busy: true });
      const { audience, conversationId } = get();
      try {
        await stream(
          { ...request, audience, ...(conversationId ? { conversation_id: conversationId } : {}) },
          (event) => {
            switch (event.type) {
              case "stage":
                patch(assistantId, (m) => ({ stages: { ...m.stages, [event.name]: event.status } }));
                break;
              case "evidence":
                patch(assistantId, (m) => ({ evidence: [...m.evidence, event.data] }));
                break;
              case "token":
                patch(assistantId, (m) => ({ text: m.text + event.text }));
                break;
              case "final":
                set({ conversationId: event.data.conversation_id, selectedId: assistantId });
                patch(assistantId, () => ({
                  text: event.data.answer,
                  status: "done",
                  response: event.data,
                  evidence: event.data.evidence,
                }));
                break;
              case "error":
                patch(assistantId, () => ({ status: "error", error: event.message }));
                break;
            }
          },
        );
        patch(assistantId, (m) =>
          m.status === "streaming"
            ? { status: "error", error: "The answer stopped before it finished. Please retry." }
            : {},
        );
      } catch (error) {
        const message = error instanceof Error ? error.message : "Network error.";
        patch(assistantId, () => ({ status: "error", error: message }));
      } finally {
        set({ busy: false });
      }
    };

    return {
      audience: "general",
      messages: [],
      busy: false,
      setAudience: (audience) => set({ audience }),
      select: (selectedId) => set({ selectedId }),
      reset: () => {
        if (get().busy) return;
        set({ messages: [], conversationId: undefined, selectedId: undefined });
      },
      async send(text, extras) {
        const request = { message: text, ...extras };
        const assistantId = id();
        set((state) => ({
          selectedId: assistantId,
          messages: [
            ...state.messages,
            { id: id(), role: "user", text, status: "done", stages: {}, evidence: [] },
            {
              id: assistantId,
              role: "assistant",
              text: "",
              status: "streaming",
              stages: {},
              evidence: [],
              request,
            },
          ],
        }));
        await run(assistantId, request);
      },
      addExchange(question, response) {
        const assistantId = id();
        set((state) => ({
          selectedId: assistantId,
          conversationId: response.conversation_id,
          messages: [
            ...state.messages,
            { id: id(), role: "user", text: question, status: "done", stages: {}, evidence: [] },
            {
              id: assistantId,
              role: "assistant",
              text: response.answer,
              status: "done",
              stages: {},
              evidence: response.evidence,
              response,
            },
          ],
        }));
      },
      async retry(assistantId) {
        const message = get().messages.find((m) => m.id === assistantId);
        if (!message?.request) return;
        patch(assistantId, () => ({ text: "", status: "streaming", error: undefined, stages: {}, evidence: [] }));
        await run(assistantId, message.request);
      },
    };
  });
}
