import { Check, LoaderCircle } from "lucide-react";
import { cn } from "cn";

import type { StageName } from "@/lib/api/client";
import type { Lang } from "@/lib/api/types";
import { STAGE_LABELS } from "@/lib/i18n";

export const STAGES: StageName[] = ["understand", "resolve", "policy", "evidence", "generate", "verify"];

export function StageProgress({
  stages,
  lang = "en",
}: {
  stages: Partial<Record<StageName, "start" | "done">>;
  lang?: Lang;
}) {
  return (
    <ol aria-label="Pipeline stages" className="flex flex-col gap-2 text-sm">
      {STAGES.map((name) => {
        const status = stages[name] ?? "pending";
        return (
          <li
            key={name}
            data-status={status}
            className={cn(
              "flex items-center gap-2.5",
              status === "pending" ? "text-muted-foreground/50" : "text-foreground",
            )}
          >
            <span
              aria-hidden
              className={cn(
                "flex size-4 shrink-0 items-center justify-center border",
                status === "done" && "border-primary bg-primary text-primary-foreground",
                status === "start" && "border-primary text-primary",
                status === "pending" && "border-border",
              )}
            >
              {status === "done" ? (
                <Check className="size-3" strokeWidth={3} />
              ) : status === "start" ? (
                <LoaderCircle className="size-3 animate-spin" />
              ) : null}
            </span>
            {STAGE_LABELS[name][lang]}
          </li>
        );
      })}
    </ol>
  );
}

/** The stage currently running (or the last finished one), for a one-line live status. */
export function currentStage(stages: Partial<Record<StageName, "start" | "done">>): StageName | undefined {
  return STAGES.findLast((name) => stages[name] === "start") ?? STAGES.findLast((name) => stages[name] === "done");
}
