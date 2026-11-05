"use client";

import { Ban, CircleHelp, Copy, LoaderCircle, PanelRight, RotateCcw, ShieldX } from "lucide-react";
import { cn } from "cn";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Scorecard } from "@/components/job/Scorecard";
import { currentStage } from "@/components/trace/StageProgress";
import type { Capability, Lang } from "@/lib/api/types";
import { numberSources } from "@/lib/citations";
import { CAPABILITY_LABELS, STAGE_LABELS, t } from "@/lib/i18n";
import type { UIMessage } from "@/lib/store";
import { AnswerBody } from "./AnswerBody";
import { CapabilityBadge, isRefusal } from "./CapabilityBadge";
import { ClarifyOptions } from "./ClarifyOptions";

const NOTICE_ICON: Partial<Record<Capability, typeof Ban>> = {
  clarify: CircleHelp,
  refuse_unpublished: ShieldX,
  refuse_action: Ban,
  out_of_scope: Ban,
};

export function MessageBubble({
  message,
  lang,
  busy,
  selected,
  onSend,
  onRetry,
  onInspect,
}: {
  message: UIMessage;
  lang: Lang;
  busy?: boolean;
  selected?: boolean;
  onSend?: (text: string) => void;
  onRetry?: (id: string) => void;
  /** Show this answer's sources; `source` focuses one numbered source. */
  onInspect?: (id: string, source?: number) => void;
}) {
  if (message.role === "user") {
    return (
      <div dir="auto" className="ms-auto max-w-[85%] whitespace-pre-wrap bg-muted px-4 py-2.5 text-[15px] leading-7">
        {message.text}
      </div>
    );
  }

  const response = message.response;
  const answerLang = response?.trace.language ?? lang;
  const capability = response?.capability;
  const notice = capability && (isRefusal(capability) || capability === "clarify");
  const NoticeIcon = capability ? NOTICE_ICON[capability] : undefined;
  const streaming = message.status === "streaming";
  const stage = currentStage(message.stages);
  const sources = response ? numberSources(response) : [];

  return (
    <article
      aria-busy={streaming}
      aria-label={lang === "fa" ? "پاسخ دستیار" : "Agent answer"}
      className={cn(
        "group/answer flex min-w-0 flex-col gap-3 border-s-2 ps-4 transition-colors",
        selected ? "border-primary" : "border-border",
      )}
    >
      {notice && capability ? (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          {NoticeIcon ? <NoticeIcon className="size-4 shrink-0" aria-hidden /> : null}
          <p dir="auto">{CAPABILITY_LABELS[capability][answerLang]}</p>
        </div>
      ) : null}

      {response && message.status === "done" ? (
        <AnswerBody
          response={response}
          sources={sources}
          lang={answerLang}
          onOpenSource={(n) => onInspect?.(message.id, n)}
        />
      ) : message.text ? (
        <p dir="auto" className="whitespace-pre-wrap text-[15px] leading-7">
          {message.text}
        </p>
      ) : null}

      {streaming ? (
        <p className="flex items-center gap-2 text-sm text-muted-foreground" aria-live="polite">
          <LoaderCircle className="size-4 animate-spin text-primary" aria-hidden />
          {stage ? STAGE_LABELS[stage][lang] : t("thinking", lang)}…
        </p>
      ) : null}

      {message.status === "error" ? (
        <div role="alert" className="flex flex-wrap items-center gap-3 text-sm text-destructive">
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
        <audio controls autoPlay src={`data:audio/mpeg;base64,${response.audio_b64}`} className="h-9 w-full max-w-sm" />
      ) : null}

      {response ? (
        <div className="flex items-center gap-1 text-muted-foreground">
          {!notice ? <CapabilityBadge capability={response.capability} lang={answerLang} /> : null}
          {onInspect ? (
            <Button variant="ghost" size="xs" onClick={() => onInspect(message.id)}>
              <PanelRight /> {t("why", lang)}
              {sources.length ? ` (${sources.length})` : ""}
            </Button>
          ) : null}
          <Button
            variant="ghost"
            size="icon-xs"
            aria-label={t("copy", lang)}
            onClick={() =>
              navigator.clipboard?.writeText(response.answer).then(
                () => toast.success(t("copied", lang)),
                () => {},
              )
            }
          >
            <Copy />
          </Button>
        </div>
      ) : null}
    </article>
  );
}
