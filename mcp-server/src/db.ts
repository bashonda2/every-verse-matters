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
