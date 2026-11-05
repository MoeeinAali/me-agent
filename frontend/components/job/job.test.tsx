import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { Scorecard as ScorecardData } from "@/lib/api/types";
import { fixtureResponse } from "@/test/fixtures";
import { JobAttach, MAX_PDF_BYTES } from "./JobAttach";
import { Scorecard } from "./Scorecard";

describe("JobAttach", () => {
  it("has URL, text and PDF tabs", () => {
    render(<JobAttach lang="en" onSubmit={() => {}} />);
    expect(screen.getAllByRole("tab").map((t) => t.textContent)).toEqual(["Link", "Paste text", "PDF"]);
  });

  it("submits a job URL", async () => {
    const submit = vi.fn();
    render(<JobAttach lang="en" onSubmit={submit} />);
    await userEvent.type(screen.getByLabelText("Job posting link"), "https://career.hrcando.ir/co/Milli/job-detail/abc");
    await userEvent.click(screen.getByRole("button", { name: "Check fit" }));
    expect(submit).toHaveBeenCalledWith({ kind: "url", url: "https://career.hrcando.ir/co/Milli/job-detail/abc" });
  });

  it("rejects a PDF over 2 MB without a request", async () => {
    const submit = vi.fn();
    render(<JobAttach lang="en" onSubmit={submit} />);
    await userEvent.click(screen.getByRole("tab", { name: "PDF" }));
    const big = new File([new Uint8Array(MAX_PDF_BYTES + 1)], "job.pdf", { type: "application/pdf" });
    await userEvent.upload(screen.getByLabelText("Job posting PDF"), big);
    expect(screen.getByRole("alert")).toHaveTextContent("2 MB");
    expect(screen.getByRole("button", { name: "Check fit" })).toBeDisabled();
    expect(submit).not.toHaveBeenCalled();
  });
});

describe("Scorecard", () => {
  it("renders coverage, verdict, row status and evidence chips in a scroll container", () => {
    const scorecard: ScorecardData = {
      job: { source: "hrcando", title: "Frontend Engineer", company: "Milli" },
      rows: [
        { requirement: "React", category: "must", kind: "skill", status: "matched", evidence: ["E1"] },
        { requirement: "Go", category: "nice", kind: "skill", status: "partial", evidence: [] },
        { requirement: "5 years", category: "must", kind: "experience", status: "no_evidence", evidence: [] },
      ],
      coverage: 0.583,
      verdict: "partial",
    };
    const { container } = render(<Scorecard scorecard={scorecard} evidence={fixtureResponse({}).evidence} lang="en" />);
    expect(screen.getByText("58%")).toBeInTheDocument();
    expect(screen.getByText("Partial fit")).toBeInTheDocument();
    expect(screen.getByText("Matched")).toBeInTheDocument();
    expect(screen.getByText("Partly")).toBeInTheDocument();
    expect(screen.getByText("No evidence")).toBeInTheDocument();
    expect(screen.getAllByText("must")).toHaveLength(2);
    expect(screen.getByText("E1")).toBeInTheDocument();
    expect(container.querySelector("[data-slot=scroll-area] table")).not.toBeNull();
  });
});
