"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import type { Lang } from "@/lib/api/types";
import { t } from "@/lib/i18n";

export const MAX_PDF_BYTES = 2_000_000;
const MAX_JOB_CHARS = 20_000;

export type JobInput = { kind: "url"; url: string } | { kind: "text"; text: string } | { kind: "pdf"; file: File };

export function JobAttach({
  lang,
  disabled,
  onSubmit,
}: {
  lang: Lang;
  disabled?: boolean;
  onSubmit: (job: JobInput) => void;
}) {
  const [url, setUrl] = useState("");
  const [text, setText] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);

  const validUrl = /^https?:\/\/\S+$/i.test(url.trim());

  return (
    <Tabs defaultValue="url" className="flex flex-col gap-3">
      <TabsList>
        <TabsTrigger value="url">{t("jobUrl", lang)}</TabsTrigger>
        <TabsTrigger value="text">{t("jobText", lang)}</TabsTrigger>
        <TabsTrigger value="pdf">{t("jobPdf", lang)}</TabsTrigger>
      </TabsList>
      <TabsContent value="url" className="flex flex-col gap-2">
        <input
          type="url"
          aria-label={t("jobUrlInput", lang)}
          placeholder="https://career.hrcando.ir/co/…/job-detail/…"
          dir="ltr"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          className="h-9 border bg-transparent px-2 font-mono text-xs"
        />
        <Button disabled={disabled || !validUrl} onClick={() => onSubmit({ kind: "url", url: url.trim() })}>
          {t("check", lang)}
        </Button>
      </TabsContent>
      <TabsContent value="text" className="flex flex-col gap-2">
        <Textarea
          dir="auto"
          aria-label={t("jobTextInput", lang)}
          rows={8}
          maxLength={MAX_JOB_CHARS}
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
        <Button disabled={disabled || !text.trim()} onClick={() => onSubmit({ kind: "text", text: text.trim() })}>
          {t("check", lang)}
        </Button>
      </TabsContent>
      <TabsContent value="pdf" className="flex flex-col gap-2">
        <input
          type="file"
          accept="application/pdf"
          aria-label={t("jobPdfInput", lang)}
          className="text-xs"
          onChange={(e) => {
            const picked = e.target.files?.[0] ?? null;
            if (picked && picked.size > MAX_PDF_BYTES) {
              setError(t("pdfTooBig", lang));
              setFile(null);
            } else {
              setError(null);
              setFile(picked);
            }
          }}
        />
        {error ? (
          <p role="alert" className="text-xs text-destructive">
            {error}
          </p>
        ) : null}
        <Button disabled={disabled || !file} onClick={() => file && onSubmit({ kind: "pdf", file })}>
          {t("check", lang)}
        </Button>
      </TabsContent>
    </Tabs>
  );
}
