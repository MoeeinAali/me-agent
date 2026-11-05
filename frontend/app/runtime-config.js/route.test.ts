import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("next/server", () => ({ connection: async () => {} }));

import { GET } from "./route";

afterEach(() => vi.unstubAllEnvs());

describe("/runtime-config.js", () => {
  it("serves the API address from the runtime environment", async () => {
    vi.stubEnv("API_BASE_URL", "https://agent-api.example.ir");
    expect(await (await GET()).text()).toContain('"https://agent-api.example.ir"');
  });

  it("ignores values that are not plain http(s) URLs", async () => {
    vi.stubEnv("API_BASE_URL", 'javascript:alert(1)"');
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "");
    expect(await (await GET()).text()).toBe('window.__ME_AGENT_API_BASE__ = "";\n');
  });
});
