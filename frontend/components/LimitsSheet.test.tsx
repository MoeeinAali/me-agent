import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { LimitsList } from "./LimitsSheet";

describe("LimitsSheet", () => {
  it("renders forbidden actions, unpublished topics and guardrails", () => {
    render(
      <LimitsList
        lang="en"
        limits={{
          forbidden_actions: ["send_email", "future_action"],
          unpublished_topics: ["Salary expectations"],
          guardrails: ["Never invent facts"],
        }}
      />,
    );
    expect(screen.getByText("Send emails for Moeein")).toBeInTheDocument();
    expect(screen.getByText("future action")).toBeInTheDocument();
    expect(screen.getByText("Salary expectations")).toBeInTheDocument();
    expect(screen.getByText("Never invent facts")).toBeInTheDocument();
  });
});
