"use client";

import { useEffect, useRef } from "react";

import type { Lang } from "@/lib/api/types";
import type { UIMessage } from "@/lib/store";
import { MessageBubble } from "./MessageBubble";

export function MessageList({
  messages,
  lang,
  busy,
  selectedId,
  onSend,
  onRetry,
  onInspect,
}: {
  messages: UIMessage[];
  lang: Lang;
  busy: boolean;
  selectedId?: string;
  onSend: (text: string) => void;
  onRetry: (id: string) => void;
  onInspect: (id: string, source?: number) => void;
}) {
  const end = useRef<HTMLDivElement>(null);
  const last = messages.at(-1);
  useEffect(() => {
    end.current?.scrollIntoView?.({ block: "end" });
  }, [messages.length, last?.text, last?.status]);

  return (
    <div role="log" aria-live="polite" className="flex flex-col gap-8">
      {messages.map((m) => (
        <MessageBubble
          key={m.id}
          message={m}
          lang={lang}
          busy={busy}
          selected={m.id === selectedId}
          onSend={onSend}
          onRetry={onRetry}
          onInspect={onInspect}
        />
      ))}
      <div ref={end} />
    </div>
  );
}
