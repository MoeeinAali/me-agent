import { BookOpen, ExternalLink, FileText, GitBranch, Globe } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import type { Evidence, Lang } from "@/lib/api/types";

function relative(iso: string, lang: Lang, now = Date.now()): string {
  const seconds = Math.round((new Date(iso).getTime() - now) / 1000);
  const rtf = new Intl.RelativeTimeFormat(lang, { numeric: "auto" });
  const abs = Math.abs(seconds);
  if (abs < 60) return rtf.format(seconds, "second");
  if (abs < 3600) return rtf.format(Math.round(seconds / 60), "minute");
  if (abs < 86400) return rtf.format(Math.round(seconds / 3600), "hour");
  return rtf.format(Math.round(seconds / 86400), "day");
}

/** One verifiable source behind a claim: a link to check it, or the record path it came from. */
export function ProofChip({ evidence, lang }: { evidence: Evidence; lang: Lang }) {
  const { proof } = evidence;
  const body = (() => {
    switch (proof.type) {
      case "github_repo":
      case "github_commit":
        return (
          <>
            <GitBranch /> GitHub
          </>
        );
      case "live_url":
        return (
          <>
            <Globe /> {proof.status ?? "unknown"}
            {proof.checked_at ? ` · ${relative(proof.checked_at, lang)}` : ""}
          </>
        );
      case "syllabus":
        return (
          <>
            <BookOpen /> {lang === "fa" ? "سرفصل درس" : "Syllabus"}
          </>
        );
      default:
        return (
          <>
            <FileText /> <span className="truncate">{evidence.path}</span>
          </>
        );
    }
  })();
  const label = (
    <>
      <span className="text-muted-foreground">{evidence.id}</span>
      {body}
      {proof.url && proof.type !== "record" ? <ExternalLink /> : null}
    </>
  );
  const className = "max-w-full gap-1 font-mono";
  if (proof.url && proof.type !== "record") {
    return (
      <Badge
        variant="outline"
        className={className}
        title={evidence.path}
        render={<a href={proof.url} target="_blank" rel="noreferrer noopener" />}
      >
        {label}
      </Badge>
    );
  }
  return (
    <Badge variant="outline" className={className} title={evidence.value}>
      {label}
    </Badge>
  );
}
