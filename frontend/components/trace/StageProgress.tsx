import { Check, Circle, LoaderCircle } from "lucide-react";

import type { StageName } from "@/lib/api/client";
import { cn } from "cn";

export const STAGES: StageName[] = ["understand", "resolve", "policy", "evidence", "generate", "verify"];

export function StageProgress({ stages }: { stages: Partial<Record<StageName, "start" | "done">> }) {
  return (
    <ol aria-label="Pipeline stages" className="flex flex-wrap gap-x-3 gap-y-1 font-mono text-xs">
      {STAGES.map((name) => {
        const status = stages[name] ?? "pending";
        return (
          <li
            key={name}
            data-status={status}
            className={cn(
              "flex items-center gap-1",
              status === "pending" ? "text-muted-foreground/60" : status === "done" ? "text-foreground" : "text-primary",
            )}
          >
            {status === "done" ? (
              <Check className="size-3" />
            ) : status === "start" ? (
              <LoaderCircle className="size-3 animate-spin" />
            ) : (
              <Circle className="size-3" />
            )}
            {name}
          </li>
        );
      })}
    </ol>
  );
}
