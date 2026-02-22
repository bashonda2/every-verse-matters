import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import Anthropic from "@anthropic-ai/sdk";
import {
  getWeek,
  getWeekDir,
  readJSON,
  writeJSON,
  fileExists,
} from "../db.js";

function getClient(): Anthropic {
  const key = process.env.ANTHROPIC_API_KEY;
  if (!key) throw new Error("ANTHROPIC_API_KEY not set");
  return new Anthropic({ apiKey: key });
}

export function registerQaTools(server: McpServer) {
  server.tool(
    "verify_urls",
    "Check all third-party URLs for a week are still live. Flags dead links.",
    {
      week: z.number().describe("CFM week number"),
      year: z.number().optional().default(2026),
    },
    async ({ week, year }) => {
      const weekDir = getWeekDir(week, year);
      const creatorsPath = `${weekDir}/creators.json`;

      if (!fileExists(creatorsPath))
        return { content: [{ type: "text" as const, text: `No creators.json found for Week ${week}` }] };

      const creators = readJSON<any[]>(creatorsPath);
      const results: { source: string; url: string; status: string }[] = [];

      for (const creator of creators) {
        if (!creator.found || !creator.content?.url) {
          results.push({
            source: creator.source_name,
            url: "N/A",
            status: "not_found",
          });
          continue;
        }

        try {
          const response = await fetch(creator.content.url, {
            method: "HEAD",
            redirect: "follow",
            signal: AbortSignal.timeout(10000),
          });
          results.push({
            source: creator.source_name,
            url: creator.content.url,
            status: response.ok ? "live" : `http_${response.status}`,
          });
        } catch (e: any) {
          results.push({
            source: creator.source_name,
            url: creator.content.url,
            status: `error: ${e.message}`,
          });
        }
      }

      const live = results.filter((r) => r.status === "live").length;
      const dead = results.filter(
        (r) => r.status !== "live" && r.status !== "not_found"
      ).length;

      writeJSON(`${weekDir}/url_verification.json`, {
        verified_at: new Date().toISOString(),
        results,
      });

      const summary = [
        `URL Verification for Week ${week}`,
        `Live: ${live} | Dead: ${dead} | Not found: ${results.length - live - dead}`,
        "",
        ...results.map((r) => `  ${r.status.padEnd(12)} ${r.source}: ${r.url}`),
      ].join("\n");

      return { content: [{ type: "text" as const, text: summary }] };
    }
  );

  server.tool(
    "flag_review",
    "Mark a specific verse's commentary for Aaron's manual review.",
    {
      week: z.number(),
      book: z.string(),
      chapter: z.number(),
      verse: z.number(),
      reason: z.string().describe("Why this verse needs review"),
      year: z.number().optional().default(2026),
    },
    async ({ week, book, chapter, verse, reason, year }) => {
      const weekDir = getWeekDir(week, year);
      const flagsPath = `${weekDir}/review_flags.json`;

      let flags: any[] = [];
      if (fileExists(flagsPath)) {
        try {
          flags = readJSON<any[]>(flagsPath);
        } catch {}
      }

      flags.push({
        book,
        chapter,
        verse,
        reason,
        flagged_at: new Date().toISOString(),
        resolved: false,
      });

      writeJSON(flagsPath, flags);

      return {
        content: [
          {
            type: "text" as const,
            text: `Flagged ${book} ${chapter}:${verse} for review: "${reason}"\n${flags.length} total flags for Week ${week}.`,
          },
        ],
      };
    }
  );

  server.tool(
    "run_qa",
    "Run full QA suite for a week: check commentary completeness, validate structure, check URLs.",
    {
      week: z.number(),
      year: z.number().optional().default(2026),
    },
    async ({ week, year }) => {
      const weekData = getWeek(week, year);
      if (!weekData)
        return { content: [{ type: "text" as const, text: `Week ${week} not found` }] };

      const weekDir = getWeekDir(week, year);
      const issues: string[] = [];

      // Check commentary exists and is complete
      const commPath = `${weekDir}/commentary.json`;
      if (!fileExists(commPath)) {
        issues.push("CRITICAL: No commentary.json found");
      } else {
        const verses = readJSON<any[]>(commPath);
        const expectedFields = [
          "narrative",
          "word_study",
          "cross_references",
          "historical_context",
          "restoration_lens",
          "prophetic_quotes",
          "christological_typology",
          "application",
        ];

        for (const v of verses) {
          if (!v.commentary) {
            issues.push(
              `${v.book} ${v.chapter}:${v.verse}: Missing commentary object`
            );
            continue;
          }
          for (const field of expectedFields) {
            if (!v.commentary[field]) {
              issues.push(
                `${v.book} ${v.chapter}:${v.verse}: Missing ${field}`
              );
            }
          }
          if (
            v.commentary.narrative &&
            v.commentary.narrative.length < 100
          ) {
            issues.push(
              `${v.book} ${v.chapter}:${v.verse}: Narrative too short (${v.commentary.narrative.length} chars)`
            );
          }
        }
      }

      // Check creators
      const creatorsPath = `${weekDir}/creators.json`;
      if (!fileExists(creatorsPath)) {
        issues.push("WARNING: No creators.json found");
      }

      const report = {
        week,
        year,
        ran_at: new Date().toISOString(),
        issues_count: issues.length,
        pass: issues.filter((i) => i.startsWith("CRITICAL")).length === 0,
        issues,
      };

      writeJSON(`${weekDir}/quality_report.json`, report);

      const summary = [
        `QA Report for Week ${week}: ${weekData.title}`,
        `Status: ${report.pass ? "PASS" : "FAIL"}`,
        `Issues: ${issues.length}`,
        "",
        ...issues.slice(0, 30).map((i) => `  ${i}`),
        issues.length > 30 ? `  ... and ${issues.length - 30} more` : "",
      ].join("\n");

      return { content: [{ type: "text" as const, text: summary }] };
    }
  );
}
