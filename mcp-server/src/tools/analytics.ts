import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { readJSON, writeJSON, fileExists } from "../db.js";

const QUERY_LOG_PATH = "logs/query_log.json";

interface QueryLogEntry {
  id: string;
  timestamp: string;
  user_session_id: string;
  query_text: string;
  response_text: string;
  audit_result: "pass" | "fail";
  audit_reason: string;
  response_regenerated: boolean;
  fallback_triggered: boolean;
  verse_context: string;
  tools_invoked: string[];
  flagged_for_review: boolean;
}

function getQueryLog(): QueryLogEntry[] {
  if (!fileExists(QUERY_LOG_PATH)) return [];
  try {
    return readJSON<QueryLogEntry[]>(QUERY_LOG_PATH);
  } catch {
    return [];
  }
}

export function registerAnalyticsTools(server: McpServer) {
  server.tool(
    "log_query",
    "Log a user-facing AI interaction for auditability and analytics.",
    {
      user_session_id: z.string().describe("Anonymous session ID"),
      query_text: z.string(),
      response_text: z.string(),
      audit_result: z.enum(["pass", "fail"]),
      audit_reason: z.string().optional().default(""),
      response_regenerated: z.boolean().optional().default(false),
      fallback_triggered: z.boolean().optional().default(false),
      verse_context: z
        .string()
        .optional()
        .default("")
        .describe("What week/chapter/verse the user was viewing"),
      tools_invoked: z.array(z.string()).optional().default([]),
      flagged_for_review: z.boolean().optional().default(false),
    },
    async (params) => {
      const log = getQueryLog();

      const entry: QueryLogEntry = {
        id: `q_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
        timestamp: new Date().toISOString(),
        ...params,
      };

      log.push(entry);
      writeJSON(QUERY_LOG_PATH, log);

      return {
        content: [
          { type: "text" as const, text: `Logged query ${entry.id}. Total entries: ${log.length}` },
        ],
      };
    }
  );

  server.tool(
    "get_popular_queries",
    "Returns the most frequent user queries for a given time period.",
    {
      days: z
        .number()
        .optional()
        .default(7)
        .describe("Look back this many days"),
      limit: z.number().optional().default(20),
    },
    async ({ days, limit }) => {
      const log = getQueryLog();
      const cutoff = new Date(
        Date.now() - days * 24 * 60 * 60 * 1000
      ).toISOString();

      const recent = log.filter((e) => e.timestamp >= cutoff);

      // Simple frequency count on normalized queries
      const freq: Record<string, number> = {};
      for (const entry of recent) {
        const normalized = entry.query_text.toLowerCase().trim().slice(0, 100);
        freq[normalized] = (freq[normalized] ?? 0) + 1;
      }

      const sorted = Object.entries(freq)
        .sort((a, b) => b[1] - a[1])
        .slice(0, limit);

      const summary = [
        `Popular queries (last ${days} days, ${recent.length} total queries):`,
        "",
        ...sorted.map(
          ([query, count], i) => `${i + 1}. (${count}x) ${query}`
        ),
      ].join("\n");

      return { content: [{ type: "text" as const, text: summary }] };
    }
  );

  server.tool(
    "get_verse_engagement",
    "Shows which verses generate the most user questions.",
    {
      days: z.number().optional().default(30),
      limit: z.number().optional().default(20),
    },
    async ({ days, limit }) => {
      const log = getQueryLog();
      const cutoff = new Date(
        Date.now() - days * 24 * 60 * 60 * 1000
      ).toISOString();

      const recent = log.filter(
        (e) => e.timestamp >= cutoff && e.verse_context
      );

      const freq: Record<string, number> = {};
      for (const entry of recent) {
        freq[entry.verse_context] = (freq[entry.verse_context] ?? 0) + 1;
      }

      const sorted = Object.entries(freq)
        .sort((a, b) => b[1] - a[1])
        .slice(0, limit);

      const summary = [
        `Verse engagement (last ${days} days):`,
        "",
        ...sorted.map(
          ([verse, count], i) => `${i + 1}. ${verse} — ${count} queries`
        ),
      ].join("\n");

      return { content: [{ type: "text" as const, text: summary }] };
    }
  );

  server.tool(
    "get_unmet_needs",
    "Surfaces queries where the AI had audit failures, fallback triggers, or was flagged for review — indicating areas where EVM's content or AI could improve.",
    {
      days: z.number().optional().default(30),
      limit: z.number().optional().default(20),
    },
    async ({ days, limit }) => {
      const log = getQueryLog();
      const cutoff = new Date(
        Date.now() - days * 24 * 60 * 60 * 1000
      ).toISOString();

      const unmet = log.filter(
        (e) =>
          e.timestamp >= cutoff &&
          (e.audit_result === "fail" ||
            e.fallback_triggered ||
            e.flagged_for_review ||
            e.response_regenerated)
      );

      if (unmet.length === 0) {
        return {
          content: [
            {
              type: "text" as const,
              text: `No unmet needs detected in the last ${days} days. All queries handled cleanly.`,
            },
          ],
        };
      }

      const summary = [
        `Unmet needs (last ${days} days): ${unmet.length} flagged interactions`,
        "",
        ...unmet.slice(0, limit).map((e) => {
          const flags = [
            e.audit_result === "fail" ? "AUDIT_FAIL" : "",
            e.fallback_triggered ? "FALLBACK" : "",
            e.response_regenerated ? "REGENERATED" : "",
            e.flagged_for_review ? "FLAGGED" : "",
          ]
            .filter(Boolean)
            .join(", ");
          return `[${flags}] "${e.query_text.slice(0, 80)}"\n  Reason: ${e.audit_reason || "N/A"}\n  Context: ${e.verse_context || "none"}`;
        }),
      ].join("\n");

      return { content: [{ type: "text" as const, text: summary }] };
    }
  );
}
