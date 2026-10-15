import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import { MeridianApiClient } from "./client.js";
import { CapabilityEnum, GroupIdEnum, PeriodPattern } from "./types.js";

const serverName = process.env.MERIDIAN_SERVER_NAME || "meridian-usage";
const server = new McpServer({
  name: serverName,
  version: "1.0.0",
});

const client = new MeridianApiClient();

// Tool 1: usage_summary(group?, period)
server.tool(
  "usage_summary",
  {
    period: PeriodPattern.describe("last_7_days | last_30_days | ISO week (e.g. 2026-W36) | month (e.g. 2026-09)"),
    group: GroupIdEnum.optional().describe("Target group. Defaults to caller's own group."),
  },
  async ({ period, group }) => {
    const result = await client.getUsageSummary(period, group);
    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(result, null, 2),
        },
      ],
    };
  }
);

// Tool 2: top_users(group?, period, limit?)
server.tool(
  "top_users",
  {
    period: PeriodPattern.describe("last_7_days | last_30_days | ISO week | month"),
    group: GroupIdEnum.optional().describe("Target group. Defaults to caller's own group."),
    limit: z.number().int().min(1).max(25).optional().default(10).describe("Rank limit 1-25 (default 10)"),
  },
  async ({ period, group, limit }) => {
    const result = await client.getTopUsers(period, group, limit);
    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(result, null, 2),
        },
      ],
    };
  }
);

// Tool 3: capability_status(group?)
server.tool(
  "capability_status",
  {
    group: GroupIdEnum.optional().describe("Target group to inspect capabilities for"),
  },
  async ({ group }) => {
    const result = await client.getCapabilityStatus(group);
    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(result, null, 2),
        },
      ],
    };
  }
);

// Tool 4: set_capability(group, capability, enabled)
server.tool(
  "set_capability",
  {
    group: GroupIdEnum.describe("Target group"),
    capability: CapabilityEnum.describe("Capability name (usage-connector | web-search | code-execution)"),
    enabled: z.boolean().describe("Enable (true) or disable (false)"),
  },
  async ({ group, capability, enabled }) => {
    const result = await client.setCapability(group, capability, enabled);
    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(result, null, 2),
        },
      ],
    };
  }
);

export async function runServer() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error(`Meridian MCP Server (${serverName}) running on stdio transport.`);
}

if (process.argv[1]?.includes("index.ts") || process.argv[1]?.includes("index.js")) {
  runServer().catch((err) => {
    console.error("Fatal MCP error:", err);
    process.exit(1);
  });
}
