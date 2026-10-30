import { ScrollArea, ScrollBar } from "@/components/ui/scroll-area";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { Evidence, Lang, Scorecard as ScorecardData } from "@/lib/api/types";
import { ProofChip } from "@/components/trace/ProofChip";

const STATUS = { matched: "✅", partial: "🟡", no_evidence: "❌" } as const;
const VERDICT: Record<ScorecardData["verdict"], Record<Lang, string>> = {
  strong: { en: "Strong fit", fa: "تناسب قوی" },
  partial: { en: "Partial fit", fa: "تناسب نسبی" },
  weak: { en: "Weak fit", fa: "تناسب ضعیف" },
};

export function Scorecard({ scorecard, evidence, lang }: { scorecard: ScorecardData; evidence: Evidence[]; lang: Lang }) {
  const byId = new Map(evidence.map((e) => [e.id, e]));
  const pct = Math.round(scorecard.coverage * 100);
  return (
    <section aria-label="Job fit scorecard" className="flex min-w-0 flex-col gap-2 border p-3">
      <header className="flex flex-wrap items-baseline gap-x-3">
        <h3 dir="auto" className="font-mono text-sm">
          {[scorecard.job.title, scorecard.job.company].filter(Boolean).join(" · ") || "Job"}
        </h3>
        <span className="font-mono text-2xl text-primary">{pct}%</span>
        <span data-verdict={scorecard.verdict} className="text-sm">
          {VERDICT[scorecard.verdict][lang]}
        </span>
      </header>
      <ScrollArea className="w-full">
        <Table className="min-w-[36rem]">
          <TableHeader>
            <TableRow>
              <TableHead className="w-8" />
              <TableHead>{lang === "fa" ? "نیازمندی" : "Requirement"}</TableHead>
              <TableHead>{lang === "fa" ? "نوع" : "Type"}</TableHead>
              <TableHead>{lang === "fa" ? "شواهد" : "Evidence"}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {scorecard.rows.map((row, i) => (
              <TableRow key={i} data-status={row.status}>
                <TableCell aria-label={row.status}>{STATUS[row.status]}</TableCell>
                <TableCell dir="auto" className="whitespace-normal">
                  {row.requirement}
                </TableCell>
                <TableCell className="font-mono text-xs">{row.category}</TableCell>
                <TableCell>
                  <div className="flex flex-wrap gap-1">
                    {row.evidence.map((id) => {
                      const item = byId.get(id);
                      return item ? <ProofChip key={id} evidence={item} lang={lang} /> : null;
                    })}
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        <ScrollBar orientation="horizontal" />
      </ScrollArea>
    </section>
  );
}
