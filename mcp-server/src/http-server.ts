/**
 * EVM MCP HTTP Server
 *
 * Exposes user-facing MCP tools (ask, lesson_prep, compare_creators, deep_dive)
 * over Streamable HTTP on port 3001.
 *
 * Nginx proxies /api/ → localhost:3001
 * Managed by PM2 on the VPS.
 *
 * Authentication: Bearer token via MCP_HTTP_API_KEY env var.
 * Rate limiting: 60 req/min per IP (in-memory, resets on restart).
 */

import express, { Request, Response, NextFunction } from "express";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import { config } from "dotenv";
import { join, dirname } from "path";

config({ path: join(dirname(new URL(import.meta.url).pathname), "..", "..", ".env") });

import { registerUserAiTools } from "./tools/user_ai.js";

const PORT = Number(process.env.MCP_HTTP_PORT ?? 3001);
const API_KEY = process.env.MCP_HTTP_API_KEY ?? "";

// ── Simple in-memory rate limiter (60 req / min per IP) ──────────────────────
const rateLimitMap = new Map<string, { count: number; resetAt: number }>();
const RATE_LIMIT = 60;
const RATE_WINDOW_MS = 60_000;

function rateLimitMiddleware(req: Request, res: Response, next: NextFunction) {
  if (req.path === "/api/health") return next();

  const ip = (req.headers["x-forwarded-for"] as string)?.split(",")[0]?.trim() ?? req.ip ?? "unknown";
  const now = Date.now();
  const entry = rateLimitMap.get(ip);

  if (!entry || now > entry.resetAt) {
    rateLimitMap.set(ip, { count: 1, resetAt: now + RATE_WINDOW_MS });
    return next();
  }

  if (entry.count >= RATE_LIMIT) {
    res.status(429).json({ error: "Rate limit exceeded. Try again in a minute." });
    return;
  }

  entry.count++;
  next();
}

// ── API key auth ──────────────────────────────────────────────────────────────
function authMiddleware(req: Request, res: Response, next: NextFunction) {
  if (req.path === "/api/health") return next();

  if (API_KEY) {
    const auth = req.headers.authorization ?? "";
    if (!auth.startsWith("Bearer ") || auth.slice(7) !== API_KEY) {
      res.status(401).json({ error: "Unauthorized" });
      return;
    }
  }
  next();
}

// ── App ───────────────────────────────────────────────────────────────────────
const app = express();
app.use(express.json({ limit: "1mb" }));
app.use(rateLimitMiddleware);
app.use(authMiddleware);

// Health check — unauthenticated
app.get("/api/health", (_req: Request, res: Response) => {
  res.json({ status: "ok", service: "evm-mcp-http", version: "0.1.0", port: PORT });
});

/**
 * MCP Streamable HTTP endpoint.
 *
 * Stateless mode: each request creates a fresh McpServer + transport pair.
 * Only user-facing tools are registered (ask, lesson_prep, compare_creators, deep_dive).
 * Admin tools (content generation, publishing, QA, analytics) are NOT exposed.
 */
app.all("/api/mcp", async (req: Request, res: Response) => {
  try {
    const mcpServer = new McpServer({ name: "evm", version: "0.1.0" });
    registerUserAiTools(mcpServer);

    const transport = new StreamableHTTPServerTransport({
      sessionIdGenerator: undefined, // stateless — no session state maintained
    });

    await mcpServer.connect(transport);
    await transport.handleRequest(req as any, res as any, req.body);
  } catch (err) {
    console.error("MCP request error:", err);
    if (!res.headersSent) {
      res.status(500).json({ error: "Internal server error" });
    }
  }
});

app.listen(PORT, "127.0.0.1", () => {
  console.log(`EVM MCP HTTP server listening on 127.0.0.1:${PORT}`);
  console.log(`Auth: ${API_KEY ? "enabled" : "DISABLED — set MCP_HTTP_API_KEY in .env"}`);
});
