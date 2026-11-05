"use client";

import { ShieldAlert } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import type { Lang, Limits } from "@/lib/api/types";
import { actionLabel, t, topicLabel } from "@/lib/i18n";

/** The same limits the model's system prompt is built from (GET /v1/limits). */
export function LimitsList({ limits, lang }: { limits: Limits; lang: Lang }) {
  const sections = [
    { title: t("forbidden", lang), items: limits.forbidden_actions.map((a) => actionLabel(a, lang)) },
    { title: t("unpublished", lang), items: limits.unpublished_topics.map((x) => topicLabel(x, lang)) },
    // Guardrails are the exact English sentences the model is instructed with.
    { title: t("guardrails", lang), items: limits.guardrails, dir: "ltr" as const },
  ];
  return (
    <div className="flex flex-col gap-6 p-4">
      {sections.map(({ title, items, dir }) => (
        <section key={title} className="flex flex-col gap-1">
          <h3 className="text-sm text-muted-foreground">{title}</h3>
          <ul dir={dir ?? "auto"} className="flex list-disc flex-col gap-1 ps-4 text-sm leading-6">
            {items.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}

export function LimitsSheet({ lang, limits, failed }: { lang: Lang; limits: Limits | null; failed: boolean }) {
  return (
    <Sheet>
      <SheetTrigger render={<Button variant="ghost" size="sm" aria-label={t("limits", lang)} />}>
        <ShieldAlert /> <span className="hidden sm:inline">{t("limits", lang)}</span>
      </SheetTrigger>
      <SheetContent className="overflow-y-auto">
        <SheetHeader>
          <SheetTitle>{t("limits", lang)}</SheetTitle>
          <SheetDescription>{t("limitsIntro", lang)}</SheetDescription>
        </SheetHeader>
        {limits ? (
          <LimitsList limits={limits} lang={lang} />
        ) : (
          <p className="p-4 text-sm text-muted-foreground">{failed ? t("limitsFailed", lang) : "…"}</p>
        )}
      </SheetContent>
    </Sheet>
  );
}
