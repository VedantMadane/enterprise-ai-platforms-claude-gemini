import { z } from "zod";

export const GroupIdEnum = z.enum([
  "clinical-operations",
  "regulatory-affairs",
  "finance",
  "hr",
  "medical-writing",
  "it-platform",
]);
export type GroupId = z.infer<typeof GroupIdEnum>;

export const PeriodPattern = z.string().regex(
  /^(last_7_days|last_30_days|\d{4}-W\d{2}|\d{4}-\d{2})$/,
  "Must be 'last_7_days', 'last_30_days', ISO week 'YYYY-Www', or month 'YYYY-MM'"
);

export const CapabilityEnum = z.enum([
  "usage-connector",
  "web-search",
  "code-execution",
]);
export type Capability = z.infer<typeof CapabilityEnum>;

export interface DenialResponse {
  error: "permission_denied";
  reason: string;
  required_scope?: string;
}

export interface PlatformTotals {
  platform: "claude" | "gemini";
  requests: number | null;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  cost_usd: number;
}

export interface UsageSummaryOutput {
  group: string;
  period: {
    start: string;
    end_exclusive: string;
  };
  platforms: PlatformTotals[];
  totals: {
    total_tokens: number;
    cost_usd: number;
  };
}

export interface TopUserOutput {
  user_id: string;
  name: string;
  email?: string;
  group: string;
  total_tokens: number;
  cost_usd: number;
}

export interface CapabilityStatusOutput {
  group: string;
  capability: Capability;
  enabled: boolean;
  updated_at: string | null;
  updated_by: string | null;
}

export interface SetCapabilityOutput {
  group: string;
  capability: Capability;
  enabled: boolean;
  updated_at: string;
  updated_by: string;
}
