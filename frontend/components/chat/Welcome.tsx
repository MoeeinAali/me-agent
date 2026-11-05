"use client";

import { Briefcase } from "lucide-react";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { Audience, type Lang } from "@/lib/api/types";
import { AUDIENCE_LABELS, t } from "@/lib/i18n";

/** The empty state: who the agent speaks for, who is asking, and what to ask first. */
export function Welcome({
  lang,
  audience,
  onAudience,
  suggestions,
  onPick,
  onJob,
}: {
  lang: Lang;
  audience: Audience;
  onAudience: (a: Audience) => void;
  suggestions: string[];
  onPick: (text: string) => void;
  onJob: () => void;
}) {
  return (
    <div className="flex flex-col gap-10 py-6 md:py-12">
      <section className="flex flex-col gap-5">
        <div className="flex items-center gap-4">
          <Avatar className="size-14 rounded-none border">
            <AvatarImage src="/images/avatar.jpg" alt="" className="rounded-none" />
            <AvatarFallback className="rounded-none">MA</AvatarFallback>
          </Avatar>
          <div>
            <p className="font-heading text-lg">{t("name", lang)}</p>
            <p className="text-sm text-muted-foreground">{t("role", lang)}</p>
          </div>
        </div>
        <h1 className="max-w-xl font-heading text-2xl leading-tight text-balance md:text-3xl">{t("title", lang)}</h1>
        <p className="max-w-xl text-[15px] leading-7 text-muted-foreground text-pretty">{t("intro", lang)}</p>
      </section>

      <section aria-labelledby="who" className="flex flex-col gap-3">
        <div>
          <h2 id="who" className="text-sm">
            {t("whoAsking", lang)}
          </h2>
          <p className="text-xs text-muted-foreground">{t("whoAskingHint", lang)}</p>
        </div>
        <ToggleGroup
          aria-labelledby="who"
          variant="outline"
          spacing={0}
          value={[audience]}
          onValueChange={(v) => v[0] && onAudience(Audience.parse(v[0]))}
          className="flex-wrap"
        >
          {Audience.options.map((a) => (
            <ToggleGroupItem
              key={a}
              value={a}
              className="data-pressed:border-primary data-pressed:bg-primary/10 data-pressed:text-primary"
            >
              {AUDIENCE_LABELS[a][lang]}
            </ToggleGroupItem>
          ))}
        </ToggleGroup>
      </section>

      <section aria-labelledby="try" className="flex flex-col gap-3">
        <h2 id="try" className="text-sm">
          {t("tryAsking", lang)}
        </h2>
        <ul className="flex flex-col border-t">
          {suggestions.map((s) => (
            <li key={s} className="border-b">
              <button
                type="button"
                dir="auto"
                onClick={() => onPick(s)}
                className="w-full py-3 text-start text-[15px] transition-colors hover:text-primary focus-visible:text-primary focus-visible:outline-none"
              >
                {s}
              </button>
            </li>
          ))}
          <li>
            <button
              type="button"
              onClick={onJob}
              className="flex w-full items-start gap-3 py-4 text-start transition-colors hover:text-primary focus-visible:text-primary focus-visible:outline-none"
            >
              <Briefcase className="mt-1 size-4 shrink-0 text-primary" aria-hidden />
              <span className="flex flex-col gap-0.5">
                <span className="text-[15px]">{t("jobCardTitle", lang)}</span>
                <span className="text-sm text-muted-foreground">{t("jobCardBody", lang)}</span>
              </span>
            </button>
          </li>
        </ul>
      </section>
    </div>
  );
}
