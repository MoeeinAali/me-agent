"use client";

import { Paperclip } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { useStore } from "zustand";

import { Composer } from "@/components/chat/Composer";
import { MessageList } from "@/components/chat/MessageList";
import { Suggestions } from "@/components/chat/Suggestions";
import { type JobInput, JobAttach } from "@/components/job/JobAttach";
import { LimitsSheet } from "@/components/LimitsSheet";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { MicButton } from "@/components/voice/MicButton";
import { getSuggestions, postJobFit } from "@/lib/api/client";
import { Audience, type Lang } from "@/lib/api/types";
import { t } from "@/lib/i18n";
import { createChatStore } from "@/lib/store";

const AUDIENCE_LABELS: Record<Audience, Record<Lang, string>> = {
  general: { en: "General", fa: "عمومی" },
  recruiter: { en: "Recruiter", fa: "استخدام‌کننده" },
  tech_lead: { en: "Tech lead / CTO", fa: "مدیر فنی" },
  professor: { en: "Professor", fa: "استاد" },
};

export function Chat() {
  const [store] = useState(() => createChatStore());
  const { messages, busy, audience, conversationId, send, retry, setAudience, addExchange } = useStore(store);
  const [lang, setLang] = useState<Lang>("en");
  const [tts, setTts] = useState(false);
  const [jobOpen, setJobOpen] = useState(false);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [uploading, setUploading] = useState(false);
  const scroller = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let live = true;
    getSuggestions(audience, lang).then((s) => live && setSuggestions(s), () => {});
    return () => {
      live = false;
    };
  }, [audience, lang]);

  const working = busy || uploading;

  const submitJob = async (job: JobInput) => {
    setJobOpen(false);
    const question = t("jobQuestion", lang);
    if (job.kind === "url") return send(question, { job_url: job.url });
    if (job.kind === "text") return send(question, { job_text: job.text });
    const form = new FormData();
    form.append("file", job.file);
    form.append("message", question);
    form.append("audience", audience);
    if (conversationId) form.append("conversation_id", conversationId);
    setUploading(true);
    try {
      addExchange(`${question} (${job.file.name})`, await postJobFit(form));
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Job check failed.");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div lang={lang} className="mx-auto flex h-dvh max-w-3xl flex-col">
      <header className="flex flex-wrap items-center gap-2 border-b px-4 py-3">
        <div className="me-auto min-w-0">
          <h1 className="font-mono text-base">Ask Moeein</h1>
          <p dir="auto" className="text-xs text-muted-foreground">
            {t("headline", lang)}
          </p>
        </div>
        <Select value={audience} onValueChange={(v) => v && setAudience(Audience.parse(v))}>
          <SelectTrigger size="sm" aria-label="Audience">
            <SelectValue>{(v: Audience) => AUDIENCE_LABELS[v][lang]}</SelectValue>
          </SelectTrigger>
          <SelectContent>
            {Audience.options.map((a) => (
              <SelectItem key={a} value={a}>
                {AUDIENCE_LABELS[a][lang]}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button variant="ghost" size="sm" onClick={() => setLang(lang === "en" ? "fa" : "en")} aria-label="Language">
          {lang === "en" ? "فا" : "EN"}
        </Button>
        <LimitsSheet lang={lang} />
      </header>

      <div ref={scroller} className="flex-1 overflow-y-auto px-4 py-4">
        <Suggestions suggestions={suggestions} visible={messages.length === 0} onPick={(s) => void send(s)} />
        <MessageList
          messages={messages}
          lang={lang}
          busy={working}
          onSend={(text) => void send(text)}
          onRetry={(id) => void retry(id)}
        />
      </div>

      <footer className="flex flex-col gap-2 px-4 pb-4">
        <Composer
          lang={lang}
          disabled={working}
          onSubmit={(text) => void send(text)}
          actions={
            <>
              <Sheet open={jobOpen} onOpenChange={setJobOpen}>
                <SheetTrigger
                  render={<Button type="button" size="icon" variant="ghost" aria-label={t("attachJob", lang)} />}
                >
                  <Paperclip />
                </SheetTrigger>
                <SheetContent side="bottom" className="mx-auto max-w-3xl">
                  <SheetHeader>
                    <SheetTitle>{t("attachJob", lang)}</SheetTitle>
                  </SheetHeader>
                  <div className="p-4">
                    <JobAttach lang={lang} disabled={working} onSubmit={(job) => void submitJob(job)} />
                  </div>
                </SheetContent>
              </Sheet>
              <MicButton
                lang={lang}
                audience={audience}
                conversationId={conversationId}
                tts={tts}
                disabled={working}
                onResponse={(r) => addExchange(r.transcript || t("voiceQuestion", lang), r)}
              />
              <label className="flex items-center gap-1 text-xs text-muted-foreground">
                <input type="checkbox" checked={tts} onChange={(e) => setTts(e.target.checked)} />
                {t("speak", lang)}
              </label>
            </>
          }
        />
        <p dir="auto" className="text-center text-xs text-muted-foreground">
          {t("footer", lang)}
        </p>
      </footer>
    </div>
  );
}
