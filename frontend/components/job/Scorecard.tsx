import { CircleCheck, CircleDashed, CircleX } from "lucide-react";
import { cn } from "cn";

import { Badge } from "@/components/ui/badge";
import { ScrollArea, ScrollBar } from "@/components/ui/scroll-area";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ProofChip } from "@/components/trace/ProofChip";
import type { Evidence, Lang, Scorecard as ScorecardData } from "@/lib/api/types";

type Status = ScorecardData["rows"][number]["status"];

const STATUS: Record<Status, { Icon: typeof CircleCheck; className: string; label: Record<Lang, string> }> = {
  matched: { Icon: CircleCheck, className: "text-primary", label: { en: "Matched", fa: "منطبق" } },
  partial: { Icon: CircleDashed, className: "text-foreground/70", label: { en: "Partly", fa: "تا حدی" } },
  no_evidence: { Icon: CircleX, className: "text-muted-foreground", label: { en: "No evidence", fa: "بی‌مدرک" } },
};
const VERDICT: Record<ScorecardData["verdict"], Record<Lang, string>> = {
  strong: { en: "Strong fit", fa: "تناسب قوی" },
  partial: { en: "Partial fit", fa: "تناسب نسبی" },
  weak: { en: "Weak fit", fa: "تناسب ضعیف" },
};
const CATEGORY: Record<"must" | "nice", Record<Lang, string>> = {
  must: { en: "must", fa: "الزامی" },
  nice: { en: "nice", fa: "امتیاز" },
};

export function Scorecard({ scorecard, evidence, lang }: { scorecard: ScorecardData; evidence: Evidence[]; lang: Lang }) {
  const byId = new Map(evidence.map((e) => [e.id, e]));
  const pct = Math.round(scorecard.coverage * 100);
  const counts = (s: Status) => scorecard.rows.filter((r) => r.status === s).length;
  return (
    <section aria-label="Job fit scorecard" className="flex min-w-0 flex-col gap-4 border bg-card p-4">
      <header className="flex flex-col gap-3">
        <h3 dir="auto" className="font-heading text-sm">
          {[scorecard.job.title, scorecard.job.company].filter(Boolean).join(lang === "fa" ? "، " : ", ") || "Job"}
        </h3>
        <div className="flex items-end gap-3">
          <span className="font-heading text-4xl leading-none text-primary tabular-nums">{pct}%</span>
          <span data-verdict={scorecard.verdict} className="pb-0.5 text-sm">
            {VERDICT[scorecard.verdict][lang]}
          </span>
        </div>
        <div
          className="flex h-1.5 w-full overflow-hidden bg-muted"
          role="img"
          aria-label={`${counts("matched")} matched, ${counts("partial")} partly, ${counts("no_evidence")} without evidence`}
        >
          <span className="bg-primary" style={{ flexGrow: counts("matched") }} />
          <span className="bg-primary/40" style={{ flexGrow: counts("partial") }} />
          <span style={{ flexGrow: counts("no_evidence") }} />
        </div>
      </header>
      <ScrollArea className="w-full">
        <Table className="min-w-[34rem]">
          <TableHeader>
            <TableRow>
              <TableHead className="w-28">{lang === "fa" ? "وضعیت" : "Status"}</TableHead>
              <TableHead>{lang === "fa" ? "نیازمندی" : "Requirement"}</TableHead>
              <TableHead>{lang === "fa" ? "مدرک" : "Proof"}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {scorecard.rows.map((row, i) => {
              const { Icon, className, label } = STATUS[row.status];
              return (
                <TableRow key={i} data-status={row.status}>
                  <TableCell>
                    <span className={cn("flex items-center gap-1.5", className)}>
                      <Icon className="size-4" aria-hidden />
                      {label[lang]}
                    </span>
                  </TableCell>
                  <TableCell dir="auto" className="whitespace-normal">
                    <span className="me-2">{row.requirement}</span>
                    <Badge variant={row.category === "must" ? "secondary" : "outline"}>{CATEGORY[row.category][lang]}</Badge>
                  </TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-1">
                      {row.evidence.map((id) => {
                        const item = byId.get(id);
                        return item ? <ProofChip key={id} evidence={item} lang={lang} /> : null;
                      })}
                    </div>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
        <ScrollBar orientation="horizontal" />
      </ScrollArea>
    </section>
  );
}
