import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { TooltipProvider } from "@/components/ui/tooltip";
import type { ChatResponse } from "@/lib/api/types";
import { fixtureResponse } from "@/test/fixtures";
import { MAX_RECORDING_MS, MicButton } from "./MicButton";

const toastError = vi.hoisted(() => vi.fn());
vi.mock("sonner", () => ({ toast: { error: toastError } }));

class FakeRecorder {
  static last: FakeRecorder;
  state: "inactive" | "recording" = "inactive";
  mimeType = "audio/webm";
  ondataavailable: ((e: { data: Blob }) => void) | null = null;
  onstop: (() => void) | null = null;
  constructor(
    public stream: MediaStream,
    public options: MediaRecorderOptions,
  ) {
    FakeRecorder.last = this;
  }
  start() {
    this.state = "recording";
  }
  stop() {
    this.state = "inactive";
    this.ondataavailable?.({ data: new Blob(["sound"]) });
    this.onstop?.();
  }
}

const stream = { getTracks: () => [{ stop: vi.fn() }] } as unknown as MediaStream;

function renderMic(post = vi.fn<(form: FormData) => Promise<ChatResponse>>(async () => fixtureResponse({}))) {
  const onResponse = vi.fn();
  render(
    <TooltipProvider>
      <MicButton lang="en" audience="recruiter" conversationId="c-1" tts={false} onResponse={onResponse} post={post} />
    </TooltipProvider>,
  );
  return { post, onResponse };
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
  toastError.mockReset();
});

describe("MicButton", () => {
  it("is disabled with an explanation when MediaRecorder is missing", () => {
    vi.stubGlobal("MediaRecorder", undefined);
    renderMic();
    expect(screen.getByRole("button", { name: /isn't supported/ })).toBeDisabled();
  });

  it("permission denied shows a toast and does not throw", async () => {
    vi.stubGlobal("MediaRecorder", FakeRecorder);
    vi.stubGlobal("navigator", { mediaDevices: { getUserMedia: vi.fn(async () => Promise.reject(new Error("denied"))) } });
    const { post } = renderMic();
    await userEvent.click(screen.getByRole("button", { name: "Ask by voice" }));
    expect(toastError).toHaveBeenCalledWith("Microphone access was denied.");
    expect(post).not.toHaveBeenCalled();
  });

  it("stops at 60 s and posts audio, audience and conversation id", async () => {
    vi.stubGlobal("MediaRecorder", FakeRecorder);
    vi.stubGlobal("navigator", { mediaDevices: { getUserMedia: vi.fn(async () => stream) } });
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const { post, onResponse } = renderMic();
    await userEvent.click(screen.getByRole("button", { name: "Ask by voice" }));
    expect(FakeRecorder.last.options.audioBitsPerSecond).toBe(32_000);
    await act(async () => {
      vi.advanceTimersByTime(MAX_RECORDING_MS);
    });
    expect(post).toHaveBeenCalledTimes(1);
    const form = post.mock.calls[0][0];
    expect(form.get("audio")).toBeInstanceOf(Blob);
    expect(form.get("audience")).toBe("recruiter");
    expect(form.get("conversation_id")).toBe("c-1");
    expect(onResponse).toHaveBeenCalled();
  });
});
