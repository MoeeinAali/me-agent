"use client";

import { SendHorizontal } from "lucide-react";
import { type ReactNode, useState } from "react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import type { Lang } from "@/lib/api/types";
import { t } from "@/lib/i18n";

export const MAX_CHARS = 2000;

export function Composer({
  onSubmit,
  disabled,
  lang,
  actions,
}: {
  onSubmit: (text: string) => void;
  disabled?: boolean;
  lang: Lang;
  actions?: ReactNode;
}) {
  const [text, setText] = useState("");
  const trimmed = text.trim();
  const canSend = !disabled && trimmed.length > 0 && text.length <= MAX_CHARS;

  const submit = () => {
    if (!canSend) return;
    onSubmit(trimmed);
    setText("");
  };

  return (
    <form
      className="flex flex-col gap-2 border bg-card p-2"
      onSubmit={(e) => {
        e.preventDefault();
        submit();
      }}
    >
      <Textarea
        dir="auto"
        aria-label={t("placeholder", lang)}
        placeholder={t("placeholder", lang)}
        value={text}
        maxLength={MAX_CHARS}
        rows={2}
        className="max-h-48 resize-none border-0 shadow-none focus-visible:ring-0"
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
            e.preventDefault();
            submit();
          }
        }}
      />
      <div className="flex items-center gap-1">
        {actions}
        <span className="ms-auto font-mono text-xs text-muted-foreground" aria-live="polite">
          {text.length}/{MAX_CHARS}
        </span>
        <Button type="submit" size="icon" disabled={!canSend} aria-label={t("send", lang)}>
          <SendHorizontal />
        </Button>
      </div>
    </form>
  );
}
