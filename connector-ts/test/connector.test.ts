import { describe, it, expect, vi } from "vitest";
import { MeridianApiClient } from "../src/client.js";
import { PeriodPattern, GroupIdEnum, CapabilityEnum } from "../src/types.js";

describe("TypeScript Schema Validation", () => {
  it("validates allowed periods", () => {
    expect(PeriodPattern.safeParse("last_7_days").success).toBe(true);
    expect(PeriodPattern.safeParse("last_30_days").success).toBe(true);
    expect(PeriodPattern.safeParse("2026-W36").success).toBe(true);
    expect(PeriodPattern.safeParse("2026-09").success).toBe(true);
    expect(PeriodPattern.safeParse("invalid_period").success).toBe(false);
  });

  it("validates allowed group IDs", () => {
    expect(GroupIdEnum.safeParse("clinical-operations").success).toBe(true);
    expect(GroupIdEnum.safeParse("finance").success).toBe(true);
    expect(GroupIdEnum.safeParse("it-platform").success).toBe(true);
    expect(GroupIdEnum.safeParse("marketing").success).toBe(false);
  });

  it("validates capabilities", () => {
    expect(CapabilityEnum.safeParse("usage-connector").success).toBe(true);
    expect(CapabilityEnum.safeParse("web-search").success).toBe(true);
    expect(CapabilityEnum.safeParse("code-execution").success).toBe(true);
    expect(CapabilityEnum.safeParse("root-access").success).toBe(false);
  });
});

describe("MeridianApiClient Error & Denial Handling", () => {
  it("transforms 403 into structured DenialResponse", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 403,
      json: async () => ({
        detail: {
          error: "permission_denied",
          reason: "User is restricted to own group.",
          required_scope: "usage:read",
        },
      }),
    });
    global.fetch = mockFetch;

    const client = new MeridianApiClient("http://localhost:8000", "test@meridianls.example");
    const result = await client.getUsageSummary("last_30_days", "finance");

    expect(result).toHaveProperty("error", "permission_denied");
    expect((result as any).reason).toContain("User is restricted");
    expect((result as any).required_scope).toBe("usage:read");
  });

  it("handles successful usage summary response", async () => {
    const mockSummary = {
      group: "clinical-operations",
      period: { start: "2026-08-29", end_exclusive: "2026-09-28" },
      platforms: [
        { platform: "claude", requests: 100, input_tokens: 5000, output_tokens: 2000, total_tokens: 7000, cost_usd: 12.5 },
        { platform: "gemini", requests: null, input_tokens: 6000, output_tokens: 3000, total_tokens: 9000, cost_usd: 8.2 },
      ],
      totals: { total_tokens: 16000, cost_usd: 20.7 },
    };

    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => mockSummary,
    });
    global.fetch = mockFetch;

    const client = new MeridianApiClient("http://localhost:8000", "priya.nair@meridianls.example");
    const result = await client.getUsageSummary("last_30_days", "clinical-operations");

    expect(result).toEqual(mockSummary);
  });
});
