"use client";

import { CloudOff, Languages, Paperclip, SquarePen, Volume2 } from "lucide-react";
import { useEffect, useState, useSyncExternalStore } from "react";
import { toast } from "sonner";
import { useStore } from "zustand";

import { Composer } from "@/components/chat/Composer";
import { MessageList } from "@/components/chat/MessageList";
import { Welcome } from "@/components/chat/Welcome";
import { Inspector } from "@/components/inspector/Inspector";
import { type JobInput, JobAttach } from "@/components/job/JobAttach";
import { LimitsSheet } from "@/components/LimitsSheet";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet";
import { Toggle } from "@/components/ui/toggle";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { MicButton } from "@/components/voice/MicButton";
import { getLimits, getReady, getSuggestions, postJobFit } from "@/lib/api/client";
import { Audience, type Lang, type Limits } from "@/lib/api/types";
import { useMediaQuery } from "@/lib/hooks/use-media-query";
import { AUDIENCE_LABELS, t } from "@/lib/i18n";
import { createChatStore } from "@/lib/store";

const noopSubscribe = () => () => {};

export function Chat() {
  const [store] = useState(() => createChatStore());
  const { messages, busy, audience, conversationId, selectedId, send, retry, setAudience, addExchange, select, reset } =
    useStore(store);
  // Persian browsers start in Persian until the visitor picks; the server always renders English.
  const browserFa = useSyncExternalStore(
    noopSubscribe,
    () => navigator.language?.toLowerCase().startsWith("fa") ?? false,
    () => false,
  );
  const [chosenLang, setLang] = useState<Lang | null>(null);
  const lang: Lang = chosenLang ?? (browserFa ? "fa" : "en");
  const [tts, setTts] = useState(false);
  const [jobOpen, setJobOpen] = useState(false);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [uploading, setUploading] = useState(false);
  const [ready, setReady] = useState(true);
  const [activeSource, setActiveSource] = useState<number>();
  const [inspectorOpen, setInspectorOpen] = useState(false);
  const [limits, setLimits] = useState<Limits | null>(null);
  const [limitsFailed, setLimitsFailed] = useState(false);
  const wide = useMediaQuery("(min-width: 1024px)");

  // Persian flips the whole page (including portalled dialogs and sheets) to right-to-left.
  useEffect(() => {
    document.documentElement.lang = lang;
    document.documentElement.dir = lang === "fa" ? "rtl" : "ltr";
  }, [lang]);

  useEffect(() => {
    let live = true;
    getSuggestions(audience, lang).then((s) => live && setSuggestions(s), () => {});
    return () => {
      live = false;
    };
  }, [audience, lang]);

  useEffect(() => {
    getLimits().then(setLimits, () => setLimitsFailed(true));
  }, []);

  useEffect(() => {
    let live = true;
    const check = () => getReady().then((ok) => live && setReady(ok));
    check();
    const timer = setInterval(check, 30_000);
    return () => {
      live = false;
      clearInterval(timer);
    };
  }, []);

  const working = busy || uploading;
  const selected = messages.find((m) => m.id === selectedId && m.role === "assistant");

  const inspect = (id: string, source?: number) => {
    select(id);
    setActiveSource(source);
    if (!wide) setInspectorOpen(true);
  };

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
      toast.error(error instanceof Error ? error.message : "The job check failed. Try again, or paste the posting's text.");
    } finally {
      setUploading(false);
    }
  };

  const inspector = <Inspector message={selected} lang={lang} activeSource={activeSource} />;

  return (
    <div className="flex h-dvh flex-col">
      <header className="flex h-14 shrink-0 items-center gap-2 border-b px-4">
        <div className="me-auto flex min-w-0 items-center gap-2.5">
          <Avatar className="size-7 rounded-none">
            <AvatarImage src="/images/avatar.jpg" alt="" className="rounded-none" />
            <AvatarFallback className="rounded-none">MA</AvatarFallback>
          </Avatar>
          <span className="truncate font-heading text-sm">
            {t("name", lang)}
            <span className="text-muted-foreground"> / agent</span>
          </span>
        </div>
        {messages.length > 0 ? (
          <Select value={audience} onValueChange={(v) => v && setAudience(Audience.parse(v))}>
            <SelectTrigger size="sm" aria-label={t("whoAsking", lang)}>
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
        ) : null}
        <Button variant="ghost" size="sm" onClick={() => setLang(lang === "en" ? "fa" : "en")} aria-label="Language">
          <Languages /> <span className={lang === "en" ? "font-[family-name:var(--font-fa)]" : ""}>{t("language", lang)}</span>
        </Button>
        <LimitsSheet lang={lang} limits={limits} failed={limitsFailed} />
        {messages.length > 0 ? (
          <Tooltip>
            <TooltipTrigger
              render={
                <Button variant="ghost" size="icon-sm" onClick={reset} disabled={working} aria-label={t("newChat", lang)} />
              }
            >
              <SquarePen />
            </TooltipTrigger>
            <TooltipContent>{t("newChat", lang)}</TooltipContent>
          </Tooltip>
        ) : null}
      </header>

      <div className="grid min-h-0 flex-1 lg:grid-cols-[minmax(0,1fr)_24rem]">
        <div className="flex min-h-0 flex-col">
          <main className="min-h-0 flex-1 overflow-y-auto">
            <div className="mx-auto flex w-full max-w-2xl flex-col gap-6 px-4 py-6">
              {!ready ? (
                <Alert>
                  <CloudOff />
                  <AlertTitle>{t("offline", lang)}</AlertTitle>
                  <AlertDescription>{t("offlineBody", lang)}</AlertDescription>
                </Alert>
              ) : null}
              {messages.length === 0 ? (
                <Welcome
                  lang={lang}
                  audience={audience}
                  onAudience={setAudience}
                  suggestions={suggestions}
                  onPick={(s) => void send(s)}
                  onJob={() => setJobOpen(true)}
                  limits={limits}
                />
              ) : (
                <MessageList
                  messages={messages}
                  lang={lang}
                  busy={working}
                  selectedId={wide ? selectedId : undefined}
                  onSend={(text) => void send(text)}
                  onRetry={(id) => void retry(id)}
                  onInspect={inspect}
                />
              )}
            </div>
          </main>

          <footer className="shrink-0 px-4 pb-3">
            <div className="mx-auto flex w-full max-w-2xl flex-col gap-2">
              <Composer
                lang={lang}
                disabled={working}
                onSubmit={(text) => void send(text)}
                actions={
                  <>
                    <Tooltip>
                      <TooltipTrigger
                        render={
                          <Button
                            type="button"
                            size="icon-sm"
                            variant="ghost"
                            aria-label={t("attachJob", lang)}
                            onClick={() => setJobOpen(true)}
                          />
                        }
                      >
                        <Paperclip />
                      </TooltipTrigger>
                      <TooltipContent>{t("attachJob", lang)}</TooltipContent>
                    </Tooltip>
                    <MicButton
                      lang={lang}
                      audience={audience}
                      conversationId={conversationId}
                      tts={tts}
                      disabled={working}
                      onResponse={(r) => addExchange(r.transcript || t("voiceQuestion", lang), r)}
                    />
                    <Tooltip>
                      <TooltipTrigger
                        render={
                          <Toggle size="sm" pressed={tts} onPressedChange={setTts} aria-label={t("speak", lang)} />
                        }
                      >
                        <Volume2 />
                      </TooltipTrigger>
                      <TooltipContent>{t("speak", lang)}</TooltipContent>
                    </Tooltip>
                  </>
                }
              />
              <p dir="auto" className="text-center text-xs text-muted-foreground">
                {t("footer", lang)}
              </p>
            </div>
          </footer>
        </div>

        <aside aria-label={t("why", lang)} className="hidden min-h-0 overflow-y-auto border-s bg-card/40 lg:block">
          {inspector}
        </aside>
      </div>

      <Sheet open={inspectorOpen && !wide} onOpenChange={setInspectorOpen}>
        <SheetContent side="bottom" className="max-h-[85dvh] overflow-y-auto">
          <SheetTitle className="sr-only">{t("why", lang)}</SheetTitle>
          {inspector}
        </SheetContent>
      </Sheet>

      <Dialog open={jobOpen} onOpenChange={setJobOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>{t("attachJob", lang)}</DialogTitle>
            <DialogDescription>{t("attachJobHint", lang)}</DialogDescription>
          </DialogHeader>
          <JobAttach lang={lang} disabled={working} onSubmit={(job) => void submitJob(job)} />
        </DialogContent>
      </Dialog>
    </div>
  );
}
