import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import Anthropic from "@anthropic-ai/sdk";
import { readFileSync } from "fs";
import { join, dirname } from "path";
import {
  getWeek,
  getConfig,
  getSources,
  getWeekDir,
  readJSON,
  writeJSON,
  fileExists,
  getRoot,
} from "../db.js";

const ROOT = getRoot();

function getClient(): Anthropic {
  const key = process.env.ANTHROPIC_API_KEY;
  if (!key) throw new Error("ANTHROPIC_API_KEY not set");
  return new Anthropic({ apiKey: key });
}

function loadPrompt(name: string): string {
  return readFileSync(
    join(ROOT, "pipeline", "prompts", `${name}.txt`),
    "utf-8"
  );
}

function extractJSON(text: string): unknown {
  let cleaned = text.trim();
  cleaned = cleaned.replace(/^```\w*\s*\n?/, "");
  cleaned = cleaned.replace(/\n?\s*```\s*$/, "");
  cleaned = cleaned.trim();

  try {
    return JSON.parse(cleaned);
  } catch {
    const arrMatch = cleaned.match(/(\[[\s\S]*\])/);
    if (arrMatch) {
      try {
        return JSON.parse(arrMatch[1]);
      } catch {}
    }
    const objMatch = cleaned.match(/(\{[\s\S]*\})/);
    if (objMatch) {
      try {
        return JSON.parse(objMatch[1]);
      } catch {}
    }
    // Try fixing trailing commas
    const fixed = cleaned.replace(/,\s*([}\]])/g, "$1");
    try {
      return JSON.parse(fixed);
    } catch {}
    const fixedArr = fixed.match(/(\[[\s\S]*\])/);
    if (fixedArr) {
      try {
        return JSON.parse(fixedArr[1]);
      } catch {}
    }
    throw new Error(
      `Could not parse JSON. First 300 chars: ${text.slice(0, 300)}`
    );
  }
}

// Verse counts for chapters used in CFM 2026
const VERSE_COUNTS: Record<string, Record<number, number>> = {
  Genesis: {
    1: 31, 2: 25, 3: 24, 4: 26, 5: 32, 6: 22, 7: 24, 8: 22, 9: 29, 10: 32,
    11: 32, 12: 20, 13: 18, 14: 24, 15: 21, 16: 16, 17: 27, 18: 33, 19: 38,
    20: 18, 21: 34, 22: 24, 23: 20, 24: 67, 25: 34, 26: 35, 27: 46, 28: 22,
    29: 35, 30: 43, 31: 55, 32: 32, 33: 20, 37: 36, 38: 30, 39: 23, 40: 23,
    41: 57, 42: 38, 43: 34, 44: 34, 45: 28, 46: 34, 47: 31, 48: 22, 49: 33,
    50: 26,
  },
};

function getVerseCount(book: string, chapter: number): number {
  return VERSE_COUNTS[book]?.[chapter] ?? 30;
}

export function registerContentTools(server: McpServer) {
  server.tool(
    "generate_commentary",
    "Generate verse-by-verse commentary for a CFM week (or a specific chapter/verse range). Calls Claude API and stores results.",
    {
      week: z.number().describe("CFM week number (1-52)"),
      year: z.number().optional().default(2026).describe("Year"),
      chapter: z
        .string()
        .optional()
        .describe("Specific chapter, e.g. 'Genesis:18'. If omitted, generates all chapters for the week."),
      verse_start: z.number().optional().describe("Start verse (requires chapter)"),
      verse_end: z.number().optional().describe("End verse (requires chapter)"),
    },
    async ({ week, year, chapter, verse_start, verse_end }) => {
      const weekData = getWeek(week, year);
      if (!weekData)
        return { content: [{ type: "text" as const, text: `Week ${week} (${year}) not found` }] };

      const config = getConfig();
      const systemPrompt = loadPrompt("commentary_system");
      const client = getClient();
      const model = config.commentary_model;
      const BATCH_SIZE = 3;

      let chapters = weekData.chapters;
      if (chapter) {
        const [book, ch] = chapter.split(":");
        chapters = [{ book, chapter: parseInt(ch) }];
      }

      const allVerses: unknown[] = [];
      const allUsage: { input: number; output: number; cost: number; seconds: number }[] = [];
      const errors: string[] = [];

      for (const ch of chapters) {
        const totalVerses = getVerseCount(ch.book, ch.chapter);
        const startV = verse_start ?? 1;
        const endV = verse_end ?? totalVerses;

        let v = startV;
        while (v <= endV) {
          const batchEnd = Math.min(v + BATCH_SIZE - 1, endV);
          const userMessage = `Generate verse-by-verse commentary for ${ch.book} chapter ${ch.chapter}, verses ${v} through ${batchEnd}. This is Week ${week} of Come, Follow Me ${year}: '${weekData.title}'. The full week's reading is ${weekData.scripture_block}. Cover every verse from ${v} to ${batchEnd}. Follow the commentary structure exactly.`;

          try {
            const start = Date.now();
            const stream = client.messages.stream({
              model,
              max_tokens: 32000,
              thinking: { type: "disabled" as const },
              system: systemPrompt,
              messages: [{ role: "user" as const, content: userMessage }],
            });
            const response = await stream.finalMessage();
            const elapsed = (Date.now() - start) / 1000;

            const textBlock = response.content.find(
              (b) => b.type === "text"
            );
            if (!textBlock || textBlock.type !== "text") {
              errors.push(`${ch.book} ${ch.chapter}:${v}-${batchEnd}: No text in response`);
              v = batchEnd + 1;
              continue;
            }

            const inputTokens = response.usage.input_tokens;
            const outputTokens = response.usage.output_tokens;
            const cost =
              (inputTokens / 1_000_000) * 1.0 +
              (outputTokens / 1_000_000) * 5.0;

            allUsage.push({
              input: inputTokens,
              output: outputTokens,
              cost,
              seconds: elapsed,
            });

            try {
              const parsed = extractJSON(textBlock.text);
              const verses = Array.isArray(parsed) ? parsed : [parsed];
              allVerses.push(...verses);
            } catch (e: any) {
              errors.push(
                `${ch.book} ${ch.chapter}:${v}-${batchEnd}: JSON parse failed — ${e.message}`
              );
              // Save raw response for debugging
              const errDir = `logs/errors`;
              writeJSON(
                `${errDir}/${ch.book}_${ch.chapter}_${v}-${batchEnd}_raw.json`,
                { text: textBlock.text, usage: { inputTokens, outputTokens }, error: e.message }
              );
            }
          } catch (e: any) {
            errors.push(`${ch.book} ${ch.chapter}:${v}-${batchEnd}: API error — ${e.message}`);
          }

          v = batchEnd + 1;
        }
      }

      // Save results
      const weekDir = getWeekDir(week, year);
      const existingPath = `${weekDir}/commentary.json`;
      let existing: unknown[] = [];
      if (fileExists(existingPath)) {
        try {
          existing = readJSON<unknown[]>(existingPath);
        } catch {}
      }

      const merged = [...existing, ...allVerses];
      writeJSON(existingPath, merged);

      const totalCost = allUsage.reduce((s, u) => s + u.cost, 0);
      const totalInput = allUsage.reduce((s, u) => s + u.input, 0);
      const totalOutput = allUsage.reduce((s, u) => s + u.output, 0);

      const metadata = {
        week,
        year,
        title: weekData.title,
        scripture_block: weekData.scripture_block,
        generated_at: new Date().toISOString(),
        model,
        verses_generated: allVerses.length,
        api_calls: allUsage.length,
        total_input_tokens: totalInput,
        total_output_tokens: totalOutput,
        estimated_cost_usd: Math.round(totalCost * 10000) / 10000,
        errors,
      };
      writeJSON(`${weekDir}/metadata.json`, metadata);

      const summary = [
        `Generated ${allVerses.length} verses for Week ${week}: ${weekData.title}`,
        `API calls: ${allUsage.length} | Tokens: ${totalInput} in / ${totalOutput} out`,
        `Estimated cost: $${totalCost.toFixed(4)}`,
        `Output: ${existingPath}`,
        errors.length > 0 ? `\nErrors (${errors.length}):\n${errors.map((e) => `  - ${e}`).join("\n")}` : "No errors.",
      ].join("\n");

      return { content: [{ type: "text" as const, text: summary }] };
    }
  );

  server.tool(
    "discover_creators",
    "Find third-party CFM content for a given week using web search. Discovers podcasts, videos, articles from tracked creators.",
    {
      week: z.number().describe("CFM week number (1-52)"),
      year: z.number().optional().default(2026),
      source_id: z.string().optional().describe("Specific source ID to search. If omitted, searches all active sources."),
    },
    async ({ week, year, source_id }) => {
      const weekData = getWeek(week, year);
      if (!weekData)
        return { content: [{ type: "text" as const, text: `Week ${week} not found` }] };

      const sources = getSources().filter((s) => s.active && (!source_id || s.id === source_id));
      const client = getClient();
      const discoveryPrompt = loadPrompt("discovery_system");

      const results: unknown[] = [];
      const errors: string[] = [];

      for (const source of sources) {
        const query = source.search_query_template.replace(
          "{scripture_block}",
          weekData.scripture_block
        );
        const userMessage = `Find the latest Come Follow Me content from ${source.name} for this week's reading: ${weekData.scripture_block} (Week ${week}: "${weekData.title}"). Search their website (${source.url}) and the web using this query: "${query}". Return the result as JSON following the output format exactly.`;

        try {
          const response = await client.messages.create({
            model: "claude-sonnet-4-5-20250929",
            max_tokens: 4000,
            tools: [{ type: "web_search_20250305" as any, name: "web_search" }],
            system: discoveryPrompt,
            messages: [{ role: "user", content: userMessage }],
          });

          const textBlock = response.content.find((b) => b.type === "text");
          if (textBlock && textBlock.type === "text") {
            try {
              const parsed = extractJSON(textBlock.text);
              results.push(parsed);
            } catch {
              results.push({
                source_name: source.name,
                source_url: source.url,
                found: false,
                content: null,
                note: "Could not parse response",
              });
            }
          }
        } catch (e: any) {
          errors.push(`${source.name}: ${e.message}`);
        }
      }

      const weekDir = getWeekDir(week, year);
      writeJSON(`${weekDir}/creators.json`, results);

      const found = results.filter((r: any) => r.found).length;
      const summary = `Discovered content from ${found}/${sources.length} sources for Week ${week}: ${weekData.title}\nOutput: ${weekDir}/creators.json${errors.length > 0 ? `\nErrors: ${errors.join(", ")}` : ""}`;

      return { content: [{ type: "text" as const, text: summary }] };
    }
  );

  server.tool(
    "search_content",
    "Search across all generated commentary for a query string. Returns matching verses.",
    {
      query: z.string().describe("Search query"),
      year: z.number().optional().default(2026),
    },
    async ({ query, year }) => {
      const schedule = readJSON<any[]>("data/cfm_schedule.json");
      const matches: { week: number; book: string; chapter: number; verse: number; snippet: string }[] = [];
      const queryLower = query.toLowerCase();

      for (const w of schedule) {
        if (w.year !== year) continue;
        const weekDir = getWeekDir(w.week, year);
        const commPath = `${weekDir}/commentary.json`;
        if (!fileExists(commPath)) continue;

        try {
          const verses = readJSON<any[]>(commPath);
          for (const v of verses) {
            const narrative = v.commentary?.narrative ?? "";
            if (narrative.toLowerCase().includes(queryLower)) {
              matches.push({
                week: w.week,
                book: v.book,
                chapter: v.chapter,
                verse: v.verse,
                snippet: narrative.slice(0, 200) + "...",
              });
            }
          }
        } catch {}
      }

      return {
        content: [
          {
            type: "text" as const,
            text: matches.length > 0
              ? `Found ${matches.length} matches for "${query}":\n\n${matches.slice(0, 20).map((m) => `${m.book} ${m.chapter}:${m.verse} (Week ${m.week})\n  ${m.snippet}`).join("\n\n")}`
              : `No matches found for "${query}"`,
          },
        ],
      };
    }
  );
}
