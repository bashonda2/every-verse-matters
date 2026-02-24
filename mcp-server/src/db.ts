import { readFileSync, writeFileSync, existsSync, mkdirSync } from "fs";
import { join, dirname } from "path";

const ROOT = join(dirname(new URL(import.meta.url).pathname), "..", "..");

export function getRoot(): string {
  return ROOT;
}

export function readJSON<T = unknown>(relativePath: string): T {
  const fullPath = join(ROOT, relativePath);
  return JSON.parse(readFileSync(fullPath, "utf-8")) as T;
}

export function writeJSON(relativePath: string, data: unknown): void {
  const fullPath = join(ROOT, relativePath);
  const dir = dirname(fullPath);
  if (!existsSync(dir)) {
    mkdirSync(dir, { recursive: true });
  }
  writeFileSync(fullPath, JSON.stringify(data, null, 2), "utf-8");
}

export function fileExists(relativePath: string): boolean {
  return existsSync(join(ROOT, relativePath));
}

export interface CfmWeek {
  week: number;
  year: number;
  date_start: string;
  date_end: string;
  title: string;
  scripture_block: string;
  chapters: { book: string; chapter: number }[];
  official_url: string;
}

export interface Source {
  id: string;
  name: string;
  tier: number;
  type: string;
  url: string;
  hosts?: string;
  specialty?: string;
  search_query_template: string;
  active: boolean;
}

export interface Config {
  commentary_model: string;
  discovery_model: string;
  max_tokens_per_chapter: number;
  pipeline_timezone: string;
  notification_email: string;
  cost_alert_threshold_weekly: number;
  anthropic_api_key_env: string;
  content_dir: string;
  log_dir: string;
}

export function getSchedule(): CfmWeek[] {
  return readJSON<CfmWeek[]>("data/cfm_schedule.json");
}

export function getWeek(weekNum: number, year = 2026): CfmWeek | undefined {
  return getSchedule().find((w) => w.week === weekNum && w.year === year);
}

export function getSources(): Source[] {
  return readJSON<Source[]>("data/sources.json");
}

export function getConfig(): Config {
  return readJSON<Config>("data/config.json");
}

export function getWeekDir(weekNum: number, year = 2026): string {
  return `content/weeks/${year}/week-${String(weekNum).padStart(2, "0")}`;
}

// ── The Covenant Rendering (TCR) ─────────────────────────────────────────────

export interface TcrKeyTerm {
  hebrew: string;
  transliteration: string;
  rendered_as: string;
  semantic_range: string;
  note: string;
}

export interface TcrVerse {
  verse: number;
  text_hebrew: string;
  text_kjv: string;
  rendering: string;
  expanded_rendering?: string;
  translator_notes: string[];
  key_terms?: TcrKeyTerm[];
  reading_level: string;
}

export interface TcrChapter {
  meta: {
    project: string;
    version: string;
    book: string;
    chapter: number;
    source_text: string;
    reference_text: string;
    model: string;
    generated_at: string;
    license: string;
  };
  verses: TcrVerse[];
}

/** Map book name to its TCR directory slug (add more as TCR expands). */
function tcrBookSlug(book: string): string | null {
  const slugs: Record<string, string> = {
    genesis: "genesis",
    Genesis: "genesis",
  };
  return slugs[book] ?? null;
}

function tcrChapterPath(book: string, chapter: number): string | null {
  const slug = tcrBookSlug(book);
  if (!slug) return null;
  const padded = String(chapter).padStart(2, "0");
  return `content/tcr/${slug}/chapter-${padded}.json`;
}

export function getTcrChapter(book: string, chapter: number): TcrChapter | null {
  const path = tcrChapterPath(book, chapter);
  if (!path || !fileExists(path)) return null;
  return readJSON<TcrChapter>(path);
}

export function getTcrVerse(book: string, chapter: number, verse: number): TcrVerse | null {
  const data = getTcrChapter(book, chapter);
  if (!data) return null;
  return data.verses.find((v) => v.verse === verse) ?? null;
}

/**
 * Returns a formatted TCR context string for AI prompts,
 * covering all chapters in a list of book+chapter references.
 */
export function getTcrContextForChapters(
  chapters: { book: string; chapter: number }[]
): string {
  const chunks: string[] = [];

  for (const { book, chapter } of chapters) {
    const data = getTcrChapter(book, chapter);
    if (!data) continue;

    for (const v of data.verses) {
      const parts: string[] = [
        `--- TCR: ${book} ${chapter}:${v.verse} ---`,
        `Hebrew: ${v.text_hebrew}`,
        `KJV: ${v.text_kjv}`,
        `TCR Rendering: ${v.rendering}`,
      ];

      if (v.expanded_rendering) {
        parts.push(`Expanded Rendering: ${v.expanded_rendering}`);
      }

      if (v.translator_notes?.length) {
        parts.push(`Translator Notes:\n${v.translator_notes.map((n) => `  • ${n}`).join("\n")}`);
      }

      if (v.key_terms?.length) {
        const terms = v.key_terms
          .map((t) => `  • ${t.hebrew} (${t.transliteration}) → "${t.rendered_as}": ${t.note}`)
          .join("\n");
        parts.push(`Key Terms:\n${terms}`);
      }

      chunks.push(parts.join("\n"));
    }
  }

  return chunks.join("\n\n");
}
