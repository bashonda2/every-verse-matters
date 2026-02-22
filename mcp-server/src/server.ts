import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import { config } from "dotenv";
import { join, dirname } from "path";

config({ path: join(dirname(new URL(import.meta.url).pathname), "..", "..", ".env") });

import { registerContentTools } from "./tools/content.js";
import { registerPublishingTools } from "./tools/publishing.js";
import { registerQaTools } from "./tools/qa.js";
import { registerUserAiTools } from "./tools/user_ai.js";
import { registerAnalyticsTools } from "./tools/analytics.js";

const server = new McpServer({
  name: "evm",
  version: "0.1.0",
});

registerContentTools(server);
registerPublishingTools(server);
registerQaTools(server);
registerUserAiTools(server);
registerAnalyticsTools(server);

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("EVM MCP Server running on stdio");
}

main().catch(console.error);
