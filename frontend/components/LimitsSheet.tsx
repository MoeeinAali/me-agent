"use client";

import { ShieldAlert } from "lucide-react";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { getLimits } from "@/lib/api/client";
import type { Lang, Limits } from "@/lib/api/types";
import { type StringKey, t } from "@/lib/i18n";

const SECTIONS: [keyof Limits, StringKey][] = [
  ["forbidden_actions", "forbidden"],
  ["unpublished_topics", "unpublished"],
  ["guardrails", "guardrails"],
];

/** The same limits the model's system prompt is built from (GET /v1/limits). */
export function LimitsList({ limits, lang }: { limits: Limits; lang: Lang }) {
  return (
    <div className="flex flex-col gap-4 p-4">
      {SECTIONS.map(([key, title]) => (
        <section key={key} className="flex flex-col gap-1">
          <h3 className="font-mono text-xs uppercase text-muted-foreground">{t(title, lang)}</h3>
          <ul dir="auto" className="list-disc ps-4 text-sm">
            {limits[key].map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}

export function LimitsSheet({ lang, load = getLimits }: { lang: Lang; load?: () => Promise<Limits> }) {
  const [limits, setLimits] = useState<Limits | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    load().then(setLimits, () => setFailed(true));
  }, [load]);

  return (
    <Sheet>
      <SheetTrigger render={<Button variant="ghost" size="sm" />}>
        <ShieldAlert /> {t("limits", lang)}
      </SheetTrigger>
      <SheetContent className="overflow-y-auto">
        <SheetHeader>
          <SheetTitle>{t("limits", lang)}</SheetTitle>
        </SheetHeader>
        {limits ? (
          <LimitsList limits={limits} lang={lang} />
        ) : (
          <p className="p-4 text-sm text-muted-foreground">{failed ? "Couldn't load the limits." : "…"}</p>
        )}
      </SheetContent>
    </Sheet>
  );
}
