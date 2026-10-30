import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { Evidence } from "@/lib/api/types";
import { fixtureResponse } from "@/test/fixtures";
import { ClaimList } from "./ClaimList";
import { ProofChip } from "./ProofChip";
import { StageProgress } from "./StageProgress";
import { TracePanel } from "./TracePanel";

const ev = (overrides: Partial<Evidence>): Evidence => ({
  id: "E1",
  path: "projects[comeback].summary",
  value: "Comeback",
  source: "record",
  trusted: true,
  proof: { type: "record" },
  ...overrides,
});

describe("StageProgress", () => {
  it("shows six stages with live status", () => {
    render(<StageProgress stages={{ understand: "done", resolve: "start" }} />);
    const items = within(screen.getByRole("list", { name: "Pipeline stages" })).getAllByRole("listitem");
    expect(items).toHaveLength(6);
    expect(items.map((i) => i.dataset.status)).toEqual(["done", "start", "pending", "pending", "pending", "pending"]);
  });
});

describe("TracePanel", () => {
  it("lists intent, capability, fields read, tools and missing facts", () => {
    const response = fixtureResponse({});
    response.trace.tools_called = [
      { name: "github", ok: true, latency_ms: 120 },
      { name: "link_check", ok: false, latency_ms: 900 },
    ];
    response.trace.missing = ["employment at Google"];
    render(<TracePanel response={response} lang="en" />);
    expect(screen.getByText("project_summary")).toBeInTheDocument();
    expect(screen.getByText("answer_from_record")).toBeInTheDocument();
    expect(screen.getByText("projects[comeback].summary", { selector: "li" })).toHaveClass("font-mono");
    expect(screen.getByText(/github · ok/)).toBeInTheDocument();
    expect(screen.getByText(/link_check · failed/)).toBeInTheDocument();
    expect(screen.getByText("employment at Google")).toBeInTheDocument();
  });
});

describe("ProofChip", () => {
  it("links GitHub proofs", () => {
    render(<ProofChip evidence={ev({ source: "github", proof: { type: "github_repo", url: "https://github.com/x/y" } })} lang="en" />);
    expect(screen.getByRole("link")).toHaveAttribute("href", "https://github.com/x/y");
  });

  it("shows live status and a relative check time", () => {
    const checked = new Date(Date.now() - 5 * 60_000).toISOString();
    render(
      <ProofChip
        evidence={ev({ proof: { type: "live_url", url: "https://comeback.top/", status: "up", checked_at: checked } })}
        lang="en"
      />,
    );
    expect(screen.getByRole("link")).toHaveTextContent(/up · 5 minutes ago/);
  });

  it("labels syllabus proofs and shows record paths", () => {
    const { rerender } = render(<ProofChip evidence={ev({ proof: { type: "syllabus", url: "https://docs.ce.sharif.edu" } })} lang="en" />);
    expect(screen.getByText(/Syllabus/)).toBeInTheDocument();
    rerender(<ProofChip evidence={ev({})} lang="en" />);
    expect(screen.getByText("projects[comeback].summary")).toBeInTheDocument();
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
  });
});

describe("ClaimList", () => {
  it("maps evidence ids to chips and skips unknown ids", () => {
    render(
      <ClaimList
        claims={[{ text: "Comeback is a PWA.", evidence: ["E1", "E9"] }]}
        evidence={[ev({})]}
        lang="en"
      />,
    );
    expect(screen.getByText("E1")).toBeInTheDocument();
    expect(screen.queryByText("E9")).not.toBeInTheDocument();
  });
});
