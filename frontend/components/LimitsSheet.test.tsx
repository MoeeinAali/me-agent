import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { LimitsList } from "./LimitsSheet";

describe("LimitsSheet", () => {
  it("renders forbidden actions, unpublished topics and guardrails", () => {
    render(
      <LimitsList
        lang="en"
        limits={{
          forbidden_actions: ["Send email on Moeein's behalf"],
          unpublished_topics: ["Salary expectations"],
          guardrails: ["Never invent facts"],
        }}
      />,
    );
    expect(screen.getByText("Send email on Moeein's behalf")).toBeInTheDocument();
    expect(screen.getByText("Salary expectations")).toBeInTheDocument();
    expect(screen.getByText("Never invent facts")).toBeInTheDocument();
  });
});
