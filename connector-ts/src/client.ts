import {
  DenialResponse,
  UsageSummaryOutput,
  TopUserOutput,
  CapabilityStatusOutput,
  SetCapabilityOutput,
} from "./types.js";

export class MeridianApiClient {
  private baseUrl: string;
  private actorEmail: string;

  constructor(
    baseUrl: string = process.env.MERIDIAN_API_URL || "http://127.0.0.1:8000",
    actorEmail: string = process.env.MERIDIAN_ACTOR_EMAIL || "priya.nair@meridianls.example"
  ) {
    this.baseUrl = baseUrl.replace(/\/$/, "");
    this.actorEmail = actorEmail;
  }

  setActorEmail(email: string) {
    this.actorEmail = email;
  }

  private async request<T>(
    path: string,
    options: RequestInit = {}
  ): Promise<T | DenialResponse> {
    const url = `${this.baseUrl}${path}`;
    const headers = {
      "Content-Type": "application/json",
      "X-Actor-Email": this.actorEmail,
      ...(options.headers || {}),
    };

    try {
      const response = await fetch(url, { ...options, headers });
      const data = await response.json();

      if (!response.ok) {
        if (response.status === 403) {
          if (data.detail && typeof data.detail === "object" && data.detail.error === "permission_denied") {
            return data.detail as DenialResponse;
          }
          return {
            error: "permission_denied",
            reason: typeof data.detail === "string" ? data.detail : "Access denied by platform policy.",
          };
        }
        return {
          error: "permission_denied",
          reason: typeof data.detail === "string" ? data.detail : `HTTP error ${response.status}`,
        };
      }

      return data as T;
    } catch (err: any) {
      return {
        error: "permission_denied",
        reason: `Failed to connect to Meridian service at ${this.baseUrl}: ${err.message}`,
      };
    }
  }

  async getUsageSummary(
    period: string,
    group?: string
  ): Promise<UsageSummaryOutput | DenialResponse> {
    let path = `/api/usage/summary?period=${encodeURIComponent(period)}`;
    if (group) path += `&group=${encodeURIComponent(group)}`;
    return this.request<UsageSummaryOutput>(path);
  }

  async getTopUsers(
    period: string,
    group?: string,
    limit: number = 10
  ): Promise<TopUserOutput[] | DenialResponse> {
    let path = `/api/usage/top-users?period=${encodeURIComponent(period)}&limit=${limit}`;
    if (group) path += `&group=${encodeURIComponent(group)}`;
    return this.request<TopUserOutput[]>(path);
  }

  async getCapabilityStatus(
    group?: string
  ): Promise<CapabilityStatusOutput[] | DenialResponse> {
    let path = `/api/capabilities`;
    if (group) path += `?group=${encodeURIComponent(group)}`;
    return this.request<CapabilityStatusOutput[]>(path);
  }

  async setCapability(
    group: string,
    capability: string,
    enabled: boolean
  ): Promise<SetCapabilityOutput | DenialResponse> {
    return this.request<SetCapabilityOutput>("/api/capabilities", {
      method: "POST",
      body: JSON.stringify({ group, capability, enabled }),
    });
  }
}
