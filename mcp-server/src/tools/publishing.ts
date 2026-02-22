import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import {
  getWeek,
  getSchedule,
  getWeekDir,
  readJSON,
  fileExists,
} from "../db.js";

export function registerPublishingTools(server: McpServer) {
  server.tool(
    "get_week",
    "Retrieve the full content package for a CFM week: commentary, creator content, and schedule metadata.",
    {
      week: z.number().describe("CFM week number (1-52)"),
      year: z.number().optional().default(2026),
    },
    async ({ week, year }) => {
      const weekData = getWeek(week, year);
      if (!weekData)
        return { content: [{ type: "text" as const, text: `Week ${week} (${year}) not found in schedule` }] };

      const weekDir = getWeekDir(week, year);

      const commPath = `${weekDir}/commentary.json`;
      const creatorsPath = `${weekDir}/creators.json`;
      const metaPath = `${weekDir}/metadata.json`;

      const commentary = fileExists(commPath)
        ? readJSON<unknown[]>(commPath)
        : null;
      const creators = fileExists(creatorsPath)
        ? readJSON<unknown[]>(creatorsPath)
        : null;
      const metadata = fileExists(metaPath)
        ? readJSON<unknown>(metaPath)
        : null;

      const verseCount = commentary ? (commentary as any[]).length : 0;
      const creatorCount = creators ? (creators as any[]).length : 0;

      const summary = [
        `Week ${week}: ${weekData.title}`,
        `Dates: ${weekData.date_start} to ${weekData.date_end}`,
        `Scripture Block: ${weekData.scripture_block}`,
        `Chapters: ${weekData.chapters.map((c) => `${c.book} ${c.chapter}`).join(", ")}`,
        `Official URL: ${weekData.official_url}`,
        ``,
        `Content Status:`,
        `  Commentary: ${commentary ? `${verseCount} verses` : "Not generated"}`,
        `  Creators: ${creators ? `${creatorCount} sources` : "Not discovered"}`,
        `  Metadata: ${metadata ? "Available" : "Not available"}`,
      ].join("\n");

      return { content: [{ type: "text" as const, text: summary }] };
    }
  );

  server.tool(
    "list_weeks",
    "List all CFM weeks for a year with their content status.",
    {
      year: z.number().optional().default(2026),
    },
    async ({ year }) => {
      const schedule = getSchedule().filter((w) => w.year === year);

      const rows = schedule.map((w) => {
        const weekDir = getWeekDir(w.week, year);
        const hasComm = fileExists(`${weekDir}/commentary.json`);
        const hasCre = fileExists(`${weekDir}/creators.json`);
        const status = hasComm && hasCre ? "✓" : hasComm ? "C" : hasCre ? "D" : "—";
        return `${String(w.week).padStart(2)} | ${w.date_start} | ${status} | ${w.title} | ${w.scripture_block}`;
      });

      const header = "Wk | Start      | St | Title | Scripture";
      const legend = "\nLegend: ✓ = complete, C = commentary only, D = creators only, — = empty";

      return {
        content: [{ type: "text" as const, text: `${header}\n${rows.join("\n")}${legend}` }],
      };
    }
  );

  server.tool(
    "get_verse",
    "Retrieve commentary for a specific verse.",
    {
      book: z.string().describe("Book name, e.g. 'Genesis'"),
      chapter: z.number().describe("Chapter number"),
      verse: z.number().describe("Verse number"),
      year: z.number().optional().default(2026),
    },
    async ({ book, chapter, verse, year }) => {
      const schedule = getSchedule().filter((w) => w.year === year);

      for (const w of schedule) {
        const match = w.chapters.find(
          (c) => c.book === book && c.chapter === chapter
        );
        if (!match) continue;

        const weekDir = getWeekDir(w.week, year);
        const commPath = `${weekDir}/commentary.json`;
        if (!fileExists(commPath)) continue;

        const verses = readJSON<any[]>(commPath);
        const found = verses.find(
          (v) => v.book === book && v.chapter === chapter && v.verse === verse
        );

        if (found) {
          return {
            content: [
              {
                type: "text" as const,
                text: JSON.stringify(found, null, 2),
              },
            ],
          };
        }
      }

      return {
        content: [
          {
            type: "text" as const,
            text: `No commentary found for ${book} ${chapter}:${verse}`,
          },
        ],
      };
    }
  );
}
