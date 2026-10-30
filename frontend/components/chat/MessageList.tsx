"use client";

import { useEffect, useRef } from "react";

import type { Lang } from "@/lib/api/types";
import type { UIMessage } from "@/lib/store";
import { MessageBubble } from "./MessageBubble";

export function MessageList({
  messages,
  lang,
  busy,
  onSend,
  onRetry,
}: {
  messages: UIMessage[];
  lang: Lang;
  busy: boolean;
  onSend: (text: string) => void;
  onRetry: (id: string) => void;
}) {
  const end = useRef<HTMLDivElement>(null);
  const last = messages.at(-1);
  useEffect(() => {
    end.current?.scrollIntoView?.({ block: "end" });
  }, [messages.length, last?.text, last?.status]);

  return (
    <div role="log" aria-live="polite" className="flex flex-col gap-4">
      {messages.map((m) => (
        <MessageBubble key={m.id} message={m} lang={lang} busy={busy} onSend={onSend} onRetry={onRetry} />
      ))}
      <div ref={end} />
    </div>
  );
}
