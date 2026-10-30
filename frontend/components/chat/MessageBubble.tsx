"use client";

import { ChevronDown, CircleHelp, Ban, RotateCcw } from "lucide-react";
import { useState } from "react";
import { cn } from "cn";

import { Button } from "@/components/ui/button";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Scorecard } from "@/components/job/Scorecard";
import { StageProgress } from "@/components/trace/StageProgress";
import { TracePanel } from "@/components/trace/TracePanel";
import type { Lang } from "@/lib/api/types";
import { t } from "@/lib/i18n";
import type { UIMessage } from "@/lib/store";
import { CapabilityBadge, isRefusal } from "./CapabilityBadge";
import { ClarifyOptions } from "./ClarifyOptions";

export function MessageBubble({
  message,
  lang,
  busy,
  onSend,
  onRetry,
}: {
  message: UIMessage;
  lang: Lang;
  busy?: boolean;
  onSend?: (text: string) => void;
  onRetry?: (id: string) => void;
}) {
  // Open while the answer streams so the live trace is visible; the user can collapse it after.
  const [open, setOpen] = useState<boolean | null>(null);

  if (message.role === "user") {
    return (
      <div dir="auto" className="ms-auto max-w-[85%] whitespace-pre-wrap bg-secondary px-3 py-2 text-sm">
        {message.text}
      </div>
    );
  }

  const response = message.response;
  const answerLang = response?.trace.language ?? lang;
  const capability = response?.capability;
  const muted = capability && (isRefusal(capability) || capability === "clarify");
  const streaming = message.status === "streaming";

  return (
    <article
      className={cn("flex min-w-0 flex-col gap-3 border p-3", muted ? "border-dashed border-muted-foreground/40" : "border-border")}
      aria-busy={streaming}
    >
      <header className="flex items-center gap-2">
        {capability ? (
          <>
            {capability === "clarify" ? (
              <CircleHelp className="size-4 text-muted-foreground" aria-hidden />
            ) : muted ? (
              <Ban className="size-4 text-muted-foreground" aria-hidden />
            ) : null}
            <CapabilityBadge capability={capability} lang={answerLang} />
          </>
        ) : null}
        {streaming ? <StageProgress stages={message.stages} /> : null}
      </header>

      {message.text ? (
        <p dir="auto" className="whitespace-pre-wrap text-sm leading-relaxed">
          {message.text}
        </p>
      ) : streaming ? (
        <p className="animate-pulse text-sm text-muted-foreground">…</p>
      ) : null}

      {message.status === "error" ? (
        <div role="alert" className="flex items-center gap-2 text-sm text-destructive">
          <span>{message.error}</span>
          {onRetry && message.request ? (
            <Button size="sm" variant="outline" disabled={busy} onClick={() => onRetry(message.id)}>
              <RotateCcw /> {t("retry", lang)}
            </Button>
          ) : null}
        </div>
      ) : null}

      {response?.clarify_options?.length && onSend ? (
        <ClarifyOptions options={response.clarify_options} onPick={onSend} disabled={busy} />
      ) : null}

      {response?.scorecard ? (
        <Scorecard scorecard={response.scorecard} evidence={response.evidence} lang={answerLang} />
      ) : null}

      {response?.audio_b64 ? (
        <audio controls autoPlay src={`data:audio/mpeg;base64,${response.audio_b64}`} className="h-8 w-full" />
      ) : null}

      {response ? (
        <Collapsible open={open ?? false} onOpenChange={setOpen}>
          <CollapsibleTrigger render={<Button variant="ghost" size="xs" className="w-fit" />}>
            <ChevronDown className={cn("transition-transform", open && "rotate-180")} /> {t("why", lang)}
          </CollapsibleTrigger>
          <CollapsibleContent className="pt-2">
            <TracePanel response={response} lang={lang} />
          </CollapsibleContent>
        </Collapsible>
      ) : null}
    </article>
  );
}
