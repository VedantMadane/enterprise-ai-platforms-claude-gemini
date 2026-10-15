# Part B Demonstration Transcript

**Assignment ID**: `Fullstack-ClaudeGemini-UsageConnector-v1`  
**Environment**: `prod`  
**Host Target**: Claude Desktop / Gemini CLI MCP stdio connector  

This transcript records the exact execution traces of the Meridian MCP Connector across allowed and denied access patterns.

---

## Scenario 1: Allowed Read (Team Lead — Own Group)
- **Caller**: `priya.nair@meridianls.example` (Role: `team_lead`, Group: `clinical-operations`)
- **Tool Call**: `usage_summary(period="last_30_days", group="clinical-operations")`
- **Result**: **200 OK** — Returns platform token breakdown and dollar costs.

```json
{
  "group": "clinical-operations",
  "period": {
    "start": "2026-08-29",
    "end_exclusive": "2026-09-28"
  },
  "platforms": [
    {
      "platform": "claude",
      "requests": 1174,
      "input_tokens": 5397300,
      "output_tokens": 742709,
      "total_tokens": 6140009,
      "cost_usd": 81.494083
    },
    {
      "platform": "gemini",
      "requests": null,
      "input_tokens": 5488080,
      "output_tokens": 1636860,
      "total_tokens": 7124940,
      "cost_usd": 10.254268
    }
  ],
  "totals": {
    "total_tokens": 13264949,
    "cost_usd": 91.748351
  }
}
```

---

## Scenario 2: Denied Cross-Group Read (Boundary Enforcement)
- **Caller**: `priya.nair@meridianls.example` (Role: `team_lead`, Group: `clinical-operations`)
- **Tool Call**: `usage_summary(period="last_30_days", group="finance")`
- **Result**: **Structured Denial** — Enforced in server code before reaching storage.

```json
{
  "error": "permission_denied",
  "reason": "User 'Priya Nair' (team_lead) is restricted to own group 'clinical-operations' and cannot view group 'finance'.",
  "required_scope": "usage:read"
}
```

---

## Scenario 3: Denied Capability Write (Role Scope Enforcement)
- **Caller**: `priya.nair@meridianls.example` (Role: `team_lead`)
- **Tool Call**: `set_capability(group="clinical-operations", capability="code-execution", enabled=true)`
- **Result**: **Structured Denial** — `capabilities:write` restricted to `platform_admin` in `prod`.

```json
{
  "error": "permission_denied",
  "reason": "Role 'team_lead' is not granted scope 'capabilities:write' in environment 'prod'.",
  "required_scope": "capabilities:write"
}
```

---

## Scenario 4: Allowed Capability Write (Platform Admin)
- **Caller**: `chloe.dubois@meridianls.example` (Role: `platform_admin`)
- **Tool Call**: `set_capability(group="clinical-operations", capability="code-execution", enabled=true)`
- **Result**: **Success** — Control persisted with timestamp and audit attribution.

```json
{
  "group": "clinical-operations",
  "capability": "code-execution",
  "enabled": true,
  "updated_at": "2026-10-15T06:55:26.647246+00:00",
  "updated_by": "chloe.dubois@meridianls.example"
}
```

---

## Scenario 5: Capability Gating Denial (`usage-connector` disabled)
- **Context**: In `prod.yaml`, `usage-connector` is default-enabled only for `clinical-operations` and `it-platform`.
- **Caller**: `chloe.dubois@meridianls.example` querying `finance`
- **Result**: **Structured Denial** — Query rejected because `usage-connector` capability is disabled for the target group.

```json
{
  "error": "permission_denied",
  "reason": "Capability 'usage-connector' is disabled for group 'finance' in environment 'prod'.",
  "required_scope": "usage:read"
}
```

---
