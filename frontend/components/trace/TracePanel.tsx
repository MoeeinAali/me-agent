import type { ReactNode } from "react";

import type { ChatResponse, Lang } from "@/lib/api/types";
import { CAPABILITY_LABELS, t } from "@/lib/i18n";
import { ClaimList } from "./ClaimList";

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="grid gap-1 sm:grid-cols-[9rem_1fr]">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="min-w-0 text-sm">{children}</dd>
    </div>
  );
}

/** The trace the assignment asks for: intent, fields read, tools, action, missing facts. */
export function TracePanel({ response, lang }: { response: ChatResponse; lang: Lang }) {
  const { trace } = response;
  const none = <span className="text-muted-foreground">{t("none", lang)}</span>;
  return (
    <div className="flex flex-col gap-4">
      <dl className="flex flex-col gap-2">
        <Row label={t("intent", lang)}>
          <code className="font-mono">{trace.intent}</code>
        </Row>
        <Row label={t("capability", lang)}>
          <code className="font-mono">{trace.capability}</code>{" "}
          <span className="text-muted-foreground">({CAPABILITY_LABELS[trace.capability][lang]})</span>
        </Row>
        <Row label={t("fields", lang)}>
          {trace.fields_read.length ? (
            <ul className="flex flex-col gap-0.5">
              {trace.fields_read.map((path) => (
                <li key={path} className="break-all font-mono text-xs">
                  {path}
                </li>
              ))}
            </ul>
          ) : (
            none
          )}
        </Row>
        <Row label={t("tools", lang)}>
          {trace.tools_called.length ? (
            <ul className="flex flex-col gap-0.5">
              {trace.tools_called.map((tool, i) => (
                <li key={i} className="break-all font-mono text-xs">
                  {tool.name} · {tool.ok ? "ok" : "failed"} · {tool.latency_ms}ms
                </li>
              ))}
            </ul>
          ) : (
            none
          )}
        </Row>
        <Row label={t("missing", lang)}>
          {trace.missing.length ? (
            <ul dir="auto" className="list-disc ps-4">
              {trace.missing.map((m) => (
                <li key={m}>{m}</li>
              ))}
            </ul>
          ) : (
            none
          )}
        </Row>
      </dl>
      <ClaimList claims={response.claims} evidence={response.evidence} lang={lang} />
      <p className="font-mono text-xs text-muted-foreground">
        trace {trace.id} · {trace.latency_ms}ms · {trace.tokens_in}+{trace.tokens_out} tokens · prompt{" "}
        {trace.prompt_version}
      </p>
    </div>
  );
}
