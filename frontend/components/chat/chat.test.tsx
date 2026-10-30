import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { UIMessage } from "@/lib/store";
import { fixtureResponse } from "@/test/fixtures";
import { ClarifyOptions } from "./ClarifyOptions";
import { Composer, MAX_CHARS } from "./Composer";
import { MessageBubble } from "./MessageBubble";
import { Suggestions } from "./Suggestions";

const assistant = (overrides: Partial<UIMessage>): UIMessage => ({
  id: "a1",
  role: "assistant",
  text: "",
  status: "done",
  stages: {},
  evidence: [],
  ...overrides,
});

describe("MessageBubble", () => {
  it("renders dir=auto and the capability badge label", () => {
    const response = fixtureResponse({ answer: "That isn't published.", capability: "refuse_unpublished" });
    render(<MessageBubble message={assistant({ text: response.answer, response })} lang="en" />);
    expect(screen.getByText("That isn't published.")).toHaveAttribute("dir", "auto");
    expect(screen.getByText("Not published")).toBeInTheDocument();
  });

  it("keeps a mixed Persian/English answer in a dir=auto block", () => {
    const text = "کامبک با Next.js و Go ساخته شده است (بیش از ۱ میلیون کاربر).";
    const response = fixtureResponse({ answer: text });
    response.trace.language = "fa";
    const { container } = render(<MessageBubble message={assistant({ text, response })} lang="en" />);
    expect(screen.getByText(text)).toHaveAttribute("dir", "auto");
    expect(screen.getByText("از رکورد")).toBeInTheDocument();
    expect(container.querySelector("article")).toMatchSnapshot();
  });

  it("an interrupted stream shows the error and a retry button", async () => {
    const onRetry = vi.fn();
    render(
      <MessageBubble
        message={assistant({ status: "error", error: "Stopped.", request: { message: "q" } })}
        lang="en"
        onRetry={onRetry}
      />,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("Stopped.");
    await userEvent.click(screen.getByRole("button", { name: /retry/i }));
    expect(onRetry).toHaveBeenCalledWith("a1");
  });

  it("renders clarify options that send the chosen label", async () => {
    const send = vi.fn();
    const response = fixtureResponse({ capability: "clarify", clarify_options: ["Comeback", "Arcadia"] });
    render(<MessageBubble message={assistant({ text: "Which one?", response })} lang="en" onSend={send} />);
    await userEvent.click(screen.getByRole("button", { name: "Comeback" }));
    expect(send).toHaveBeenCalledWith("Comeback");
  });
});

describe("ClarifyOptions", () => {
  it("click sends the label", async () => {
    const send = vi.fn();
    render(<ClarifyOptions options={["Comeback", "LakLak"]} onPick={send} />);
    await userEvent.click(screen.getByRole("button", { name: "Comeback" }));
    expect(send).toHaveBeenCalledWith("Comeback");
  });
});

describe("Composer", () => {
  it("submits on Enter, adds a newline on Shift+Enter", async () => {
    const submit = vi.fn();
    render(<Composer onSubmit={submit} lang="en" />);
    const box = screen.getByRole("textbox");
    await userEvent.type(box, "line one{Shift>}{Enter}{/Shift}line two");
    expect(box).toHaveValue("line one\nline two");
    expect(submit).not.toHaveBeenCalled();
    await userEvent.type(box, "{Enter}");
    expect(submit).toHaveBeenCalledWith("line one\nline two");
    expect(box).toHaveValue("");
  });

  it("is disabled while streaming", async () => {
    const submit = vi.fn();
    render(<Composer onSubmit={submit} lang="en" disabled />);
    await userEvent.type(screen.getByRole("textbox"), "hi{Enter}");
    expect(submit).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Send" })).toBeDisabled();
  });

  it("shows a character counter capped at 2000", () => {
    render(<Composer onSubmit={() => {}} lang="en" />);
    const box = screen.getByRole("textbox");
    expect(box).toHaveAttribute("maxlength", String(MAX_CHARS));
    fireEvent.change(box, { target: { value: "abc" } });
    expect(screen.getByText(`3/${MAX_CHARS}`)).toBeInTheDocument();
  });
});

describe("Suggestions", () => {
  it("shows only when there are no messages", () => {
    const { rerender } = render(<Suggestions suggestions={["Summarize Comeback"]} visible onPick={() => {}} />);
    expect(screen.getByText("Summarize Comeback")).toBeInTheDocument();
    rerender(<Suggestions suggestions={["Summarize Comeback"]} visible={false} onPick={() => {}} />);
    expect(screen.queryByText("Summarize Comeback")).not.toBeInTheDocument();
  });
});
