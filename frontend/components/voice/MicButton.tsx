"use client";

import { Mic, Square } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { postVoice } from "@/lib/api/client";
import type { Audience, ChatResponse, Lang } from "@/lib/api/types";
import { t } from "@/lib/i18n";

export const MAX_RECORDING_MS = 60_000;
// Low bitrate keeps a 60 s webm clip under the backend's cap for formats it cannot measure.
const AUDIO_BITS_PER_SECOND = 32_000;

export function MicButton({
  lang,
  audience,
  conversationId,
  tts,
  disabled,
  onResponse,
  post = postVoice,
}: {
  lang: Lang;
  audience: Audience;
  conversationId?: string;
  tts: boolean;
  disabled?: boolean;
  onResponse: (response: ChatResponse) => void;
  post?: (form: FormData) => Promise<ChatResponse>;
}) {
  const [recording, setRecording] = useState(false);
  const [sending, setSending] = useState(false);
  const recorder = useRef<MediaRecorder | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const supported =
    typeof window !== "undefined" &&
    typeof window.MediaRecorder !== "undefined" &&
    !!navigator.mediaDevices?.getUserMedia;

  useEffect(
    () => () => {
      if (timer.current) clearTimeout(timer.current);
      recorder.current?.stream.getTracks().forEach((track) => track.stop());
    },
    [],
  );

  const stop = () => {
    if (timer.current) clearTimeout(timer.current);
    timer.current = null;
    if (recorder.current?.state === "recording") recorder.current.stop();
  };

  const upload = async (blob: Blob) => {
    const form = new FormData();
    form.append("audio", blob, "question.webm");
    form.append("audience", audience);
    form.append("tts", String(tts));
    if (conversationId) form.append("conversation_id", conversationId);
    setSending(true);
    try {
      onResponse(await post(form));
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Voice request failed.");
    } finally {
      setSending(false);
    }
  };

  const start = async () => {
    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      toast.error(t("micDenied", lang));
      return;
    }
    const chunks: Blob[] = [];
    const rec = new MediaRecorder(stream, { audioBitsPerSecond: AUDIO_BITS_PER_SECOND });
    rec.ondataavailable = (e) => {
      if (e.data.size) chunks.push(e.data);
    };
    rec.onstop = () => {
      stream.getTracks().forEach((track) => track.stop());
      setRecording(false);
      recorder.current = null;
      if (chunks.length) void upload(new Blob(chunks, { type: rec.mimeType || "audio/webm" }));
    };
    recorder.current = rec;
    rec.start();
    setRecording(true);
    timer.current = setTimeout(stop, MAX_RECORDING_MS);
  };

  const label = !supported ? t("micUnsupported", lang) : recording ? t("stop", lang) : t("record", lang);
  return (
    <Tooltip>
      <TooltipTrigger
        render={
          <span>
            <Button
              type="button"
              size="icon"
              variant={recording ? "destructive" : "ghost"}
              aria-label={label}
              disabled={!supported || disabled || sending}
              onClick={() => (recording ? stop() : void start())}
            >
              {recording ? <Square /> : <Mic />}
            </Button>
          </span>
        }
      />
      <TooltipContent>{label}</TooltipContent>
    </Tooltip>
  );
}
