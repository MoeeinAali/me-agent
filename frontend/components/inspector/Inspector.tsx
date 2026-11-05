"use client";

import { ChevronDown, ExternalLink } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { cn } from "cn";

import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Separator } from "@/components/ui/separator";
import { CapabilityBadge } from "@/components/chat/CapabilityBadge";
import { StageProgress } from "@/components/trace/StageProgress";
import { TracePanel } from "@/components/trace/TracePanel";
import type { Lang } from "@/lib/api/types";
import { type Source, numberSources } from "@/lib/citations";
import { CAPABILITY_EXPLAINED, t } from "@/lib/i18n";
import type { UIMessage } from "@/lib/store";

function proofLabel(source: Source, lang: Lang): string | null {
  const { proof } = source;
  if (!proof.url || proof.type === "record") return null;
  switch (proof.type) {
    case "github_repo":
    case "github_commit":
      return lang === "fa" ? "در گیت‌هاب" : "View on GitHub";
    case "live_url":
      return proof.status === "down"
        ? lang === "fa" ? "سایت (از دسترس خارج)" : "Site (down at last check)"
        : lang === "fa" ? "سایت زنده" : "Live site";
    case "syllabus":
      return lang === "fa" ? "سرفصل درس" : "Course syllabus";
    default:
      return lang === "fa" ? "منبع" : "Open source";
  }
}

function SourceItem({ source, lang, active }: { source: Source; lang: Lang; active: boolean }) {
  const ref = useRef<HTMLLIElement>(null);
  useEffect(() => {
    if (active) ref.current?.scrollIntoView?.({ block: "nearest", behavior: "smooth" });
  }, [active]);
  const label = proofLabel(source, lang);
  return (
    <li
      ref={ref}
      id={`source-${source.n}`}
      className={cn(
        "flex gap-3 border-s-2 py-1 ps-3 transition-colors",
        active ? "border-primary bg-primary/5" : "border-transparent",
      )}
    >
      <span className="mt-0.5 flex h-4 min-w-4 items-center justify-center bg-primary/15 px-1 font-mono text-[10px] text-primary tabular-nums">
        {source.n}
      </span>
      <div className="flex min-w-0 flex-col gap-1">
        <p dir="auto" className="line-clamp-4 text-sm">
          {source.value}
        </p>
        <p className="break-all font-mono text-[11px] text-muted-foreground">{source.path}</p>
        {label && source.proof.url ? (
          <a
            href={source.proof.url}
            target="_blank"
            rel="noreferrer noopener"
            className="inline-flex w-fit items-center gap-1 text-xs text-primary underline-offset-4 hover:underline"
          >
            {label}
            <ExternalLink className="size-3" aria-hidden />
          </a>
        ) : null}
      </div>
    </li>
  );
}

/** Where the selected answer came from: its action, numbered sources, progress, and the raw trace. */
export function Inspector({ message, lang, activeSource }: { message?: UIMessage; lang: Lang; activeSource?: number }) {
  const [detailsOpen, setDetailsOpen] = useState(false);

  if (!message) {
    return (
      <div className="flex flex-col gap-3 p-5">
        <h2 className="font-heading text-sm">{t("why", lang)}</h2>
        <p className="text-sm text-muted-foreground">{t("inspectorEmpty", lang)}</p>
      </div>
    );
  }

  const response = message.response;
  const sources = response ? numberSources(response) : [];
  const answerLang = response?.trace.language ?? lang;

  return (
    <div className="flex flex-col gap-5 p-5">
      <section className="flex flex-col gap-2">
        <h2 className="font-heading text-sm">{t("why", lang)}</h2>
        {response ? (
          <>
            <CapabilityBadge capability={response.capability} lang={answerLang} />
            <p dir="auto" className="text-sm text-muted-foreground">
              {CAPABILITY_EXPLAINED[response.capability][answerLang]}
            </p>
          </>
        ) : null}
      </section>

      {response ? (
        <section aria-labelledby="sources-heading" className="flex flex-col gap-3">
          <h3 id="sources-heading" className="text-xs text-muted-foreground">
            {t("sources", lang)} ({sources.length})
          </h3>
          {sources.length ? (
            <ol className="flex flex-col gap-3">
              {sources.map((s) => (
                <SourceItem key={s.id} source={s} lang={answerLang} active={activeSource === s.n} />
              ))}
            </ol>
          ) : (
            <p className="text-sm text-muted-foreground">{t("noSources", lang)}</p>
          )}
        </section>
      ) : null}

      <Separator />

      <section className="flex flex-col gap-3">
        <h3 className="text-xs text-muted-foreground">{t("progress", lang)}</h3>
        <StageProgress
          stages={
            message.status === "done" && Object.keys(message.stages).length === 0
              ? { understand: "done", resolve: "done", policy: "done", evidence: "done", generate: "done", verify: "done" }
              : message.stages
          }
          lang={lang}
        />
      </section>

      {response ? (
        <Collapsible open={detailsOpen} onOpenChange={setDetailsOpen}>
          <CollapsibleTrigger className="flex w-full items-center justify-between text-xs text-muted-foreground hover:text-foreground">
            {t("details", lang)}
            <ChevronDown className={cn("size-4 transition-transform", detailsOpen && "rotate-180")} aria-hidden />
          </CollapsibleTrigger>
          <CollapsibleContent className="pt-3">
            <TracePanel response={response} lang={lang} />
          </CollapsibleContent>
        </Collapsible>
      ) : null}
    </div>
  );
}
