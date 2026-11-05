"use client";

import { HoverCard, HoverCardContent, HoverCardTrigger } from "@/components/ui/hover-card";
import { ProofChip } from "@/components/trace/ProofChip";
import type { Lang } from "@/lib/api/types";
import type { Source } from "@/lib/citations";

/** A numbered source marker after a claim. Hover previews the source; click opens it in the inspector. */
export function CitationMarker({ source, lang, onOpen }: { source: Source; lang: Lang; onOpen?: (n: number) => void }) {
  return (
    <HoverCard>
      <HoverCardTrigger
        delay={150}
        render={
          <button
            type="button"
            aria-label={`${lang === "fa" ? "منبع" : "Source"} ${source.n}`}
            onClick={() => onOpen?.(source.n)}
            className="mx-0.5 inline-flex h-4 min-w-4 -translate-y-1 items-center justify-center bg-primary/15 px-1 align-baseline font-mono text-[10px] leading-none text-primary tabular-nums transition-colors hover:bg-primary hover:text-primary-foreground focus-visible:outline-1 focus-visible:outline-primary"
          />
        }
      >
        {source.n}
      </HoverCardTrigger>
      <HoverCardContent className="w-80 max-w-[calc(100vw-2rem)]">
        <div className="flex flex-col gap-2">
          <p className="break-all font-mono text-[11px] text-muted-foreground">{source.path}</p>
          <p dir="auto" className="line-clamp-5 text-sm">
            {source.value}
          </p>
          <div>
            <ProofChip evidence={source} lang={lang} />
          </div>
        </div>
      </HoverCardContent>
    </HoverCard>
  );
}
