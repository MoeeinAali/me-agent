import { describe, expect, it } from "vitest";

import { fixtureResponse } from "@/test/fixtures";
import { numberSources, segmentAnswer } from "./citations";

describe("citations", () => {
  it("numbers cited evidence in order of first citation and skips unknown ids", () => {
    const response = fixtureResponse({});
    response.evidence.push({ ...response.evidence[0], id: "E2", path: "projects[comeback].tech" });
    response.claims = [
      { text: "A.", evidence: ["E2", "E9"] },
      { text: "B.", evidence: ["E1", "E2"] },
    ];
    expect(numberSources(response).map((s) => [s.id, s.n])).toEqual([
      ["E2", 1],
      ["E1", 2],
    ]);
  });

  it("keeps fixed text around the claims (job summary before, missing note after)", () => {
    const response = fixtureResponse({ answer: "Fit: 50%.\n\nHe knows React. Not in the record: Go." });
    response.claims = [{ text: "He knows React.", evidence: ["E1"] }];
    const segments = segmentAnswer(response, numberSources(response));
    expect(segments.map((s) => s.kind)).toEqual(["text", "claim", "text"]);
  });

  it("falls back to the plain answer when claims are not in it", () => {
    const response = fixtureResponse({ answer: "Something else entirely." });
    response.claims = [{ text: "A claim that is not there.", evidence: ["E1"] }];
    expect(segmentAnswer(response, numberSources(response))).toEqual([{ kind: "text", text: "Something else entirely." }]);
  });

  it("marks bullet claims", () => {
    const response = fixtureResponse({ answer: "- One\n- Two" });
    response.claims = [
      { text: "- One", evidence: ["E1"] },
      { text: "- Two", evidence: ["E1"] },
    ];
    const segments = segmentAnswer(response, numberSources(response));
    expect(segments).toMatchObject([
      { kind: "claim", bullet: true, text: "One" },
      { kind: "claim", bullet: true, text: "Two" },
    ]);
  });
});
