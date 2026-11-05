"use client";

import { ArrowUp } from "lucide-react";
import { type ReactNode, useState } from "react";
import { cn } from "cn";

import { Button } from "@/components/ui/button";
import { Kbd } from "@/components/ui/kbd";
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
  const nearLimit = text.length > MAX_CHARS * 0.8;

  const submit = () => {
    if (!canSend) return;
    onSubmit(trimmed);
    setText("");
  };

  return (
    <form
      className="flex flex-col border bg-card transition-colors focus-within:border-primary/60"
      onSubmit={(e) => {
        e.preventDefault();
        submit();
      }}
    >
      <textarea
        dir="auto"
        aria-label={t("placeholder", lang)}
        placeholder={t("placeholder", lang)}
        value={text}
        maxLength={MAX_CHARS}
        rows={1}
        className="field-sizing-content max-h-52 min-h-12 w-full resize-none bg-transparent px-4 pt-3 pb-1 text-[15px] leading-7 outline-none placeholder:text-muted-foreground"
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
            e.preventDefault();
            submit();
          }
        }}
      />
      <div className="flex items-center gap-1 px-2 pb-2">
        {actions}
        <span className="ms-auto hidden items-center gap-1 text-xs text-muted-foreground md:flex">
          <Kbd>Enter</Kbd> {t("enterHint", lang)}
          <span className="mx-1" />
          <Kbd>Shift</Kbd>+<Kbd>Enter</Kbd> {t("shiftEnterHint", lang)}
        </span>
        <span
          className={cn("ms-auto ps-3 font-mono text-xs tabular-nums md:ms-0", nearLimit ? "text-primary" : "text-muted-foreground/60")}
          aria-live="polite"
        >
          {text.length}/{MAX_CHARS}
        </span>
        <Button type="submit" size="icon" disabled={!canSend} aria-label={t("send", lang)} className="ms-2">
          <ArrowUp />
        </Button>
      </div>
    </form>
  );
}
