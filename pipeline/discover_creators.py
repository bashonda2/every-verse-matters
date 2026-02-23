#!/usr/bin/env python3
"""
Stage 2: Creator Discovery
Finds third-party CFM content for a given week using Claude + web search.
Runs TWO passes: 2026 current cycle + 2022 archive cycle (same scripture block,
different guest scholars/angles — both permanently relevant).

Output: content/weeks/2026/week-{nn}/creators.json
"""

import sys
import json
import re
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.utils.api_client import get_client, load_config

CONTENT_DIR = ROOT / "content" / "weeks" / "2026"
DATA_DIR = ROOT / "data"

SYSTEM_PROMPT = """You are a content discovery engine for EveryVerseMatters.com.
Find Come, Follow Me content from specific creators for a given week's scripture block.

RULES:
- Only return content that matches THIS SPECIFIC scripture block
- Return direct URLs to the specific episode, article, or video — NOT homepage links
- If you cannot find content for this specific week, return null for that creator
- Generate a 2-3 sentence summary of what makes this creator's take unique
- Include publish date and content type (podcast/video/article)
- For podcasts, include episode number if available, duration if available

Return valid JSON array. Each entry must have:
{
  "source_name": "exact name from the list",
  "source_url": "creator homepage",
  "found": true/false,
  "content": {
    "title": "...",
    "url": "direct link to THIS episode/article",
    "content_type": "podcast|video|article",
    "published_at": "YYYY-MM-DD or null",
    "episode_number": null,
    "duration_minutes": null,
    "summary": "2-3 sentences on their unique angle",
    "hosts_or_guests": "host and guest names",
    "verse_tags": ["Gen 18:1"],
    "cycle": "2026 or 2022"
  } or null if not found,
  "notes": "optional explanation if not found"
}"""


def discover_creators(week_num: int) -> list:
    schedule = json.loads((DATA_DIR / "cfm_schedule.json").read_text())
    week_data = next((w for w in schedule if w["week"] == week_num), None)
    if not week_data:
        raise ValueError(f"Week {week_num} not found")

    sources = json.loads((DATA_DIR / "sources.json").read_text())
    tier1 = [s for s in sources if s.get("tier") == 1 and s.get("active", True)]

    scripture = week_data["scripture_block"]
    title = week_data["title"]

    week_dir = CONTENT_DIR / f"week-{str(week_num).zfill(2)}"
    week_dir.mkdir(parents=True, exist_ok=True)
    creators_path = week_dir / "creators.json"

    # Load existing entries to preserve manually added ones
    existing = json.loads(creators_path.read_text()) if creators_path.exists() else []
    existing_names = {e["source_name"] for e in existing if e.get("found")}

    client = get_client()
    config = load_config()
    discovery_model = config.get("discovery_model", "claude-sonnet-4-5-20250929")

    all_results = list(existing)
    found_names = {e["source_name"] for e in all_results}

    # Split sources into batches of 5
    def search_batch(creator_names: list, cycle: str, year: int):
        creator_list = "\n".join(f"- {n}" for n in creator_names)
        year_note = f"Search for {year} content" if cycle == "2026" else f"Search for {year} ARCHIVE content (Feb {year})"

        msg = f"""Find Come, Follow Me content for: {scripture} (Week {week_num}: "{title}")
{year_note} — same scripture block.

CREATORS TO SEARCH:
{creator_list}

For each creator, search their website, Apple Podcasts, Spotify, and YouTube.
Mark cycle as "{cycle}" in each entry.

Return a JSON array (one entry per creator)."""

        try:
            response = client.messages.create(
                model=discovery_model,
                max_tokens=4000,
                tools=[{"type": "web_search_20250305", "name": "web_search"}],
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": msg}],
            )

            text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    text += block.text

            text = text.strip()
            text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.MULTILINE)
            text = re.sub(r'\s*```$', '', text, flags=re.MULTILINE)

            results = json.loads(text.strip())
            if isinstance(results, list):
                return results
        except Exception as e:
            print(f"    Batch search error: {e}")
        return []

    # 2026 pass — creators we don't already have
    new_creators = [s["name"] for s in tier1 if s["name"] not in found_names]
    if new_creators:
        print(f"\n  2026 pass — searching {len(new_creators)} creators...")
        for i in range(0, len(new_creators), 5):
            batch = new_creators[i:i+5]
            print(f"    Batch: {', '.join(batch)}")
            results = search_batch(batch, "2026", 2026)
            for r in results:
                if r.get("source_name") not in found_names:
                    all_results.append(r)
                    if r.get("found"):
                        found_names.add(r["source_name"])

    # 2022 archive pass — key creators with rich archives
    archive_creators = ["Follow Him (followHIM)", "Don't Miss This", "Unshaken Saints",
                        "Scripture Central", "Talking Scripture"]
    archive_new = [n for n in archive_creators
                   if f"{n} (2022 Archive)" not in found_names and n not in existing_names]
    if archive_new:
        print(f"\n  2022 archive pass — searching {len(archive_new)} creators...")
        results = search_batch(archive_new, "2022", 2022)
        for r in results:
            if r.get("found") and r.get("content"):
                r["source_name"] = f"{r['source_name']} (2022 Archive)"
                if r["source_name"] not in found_names:
                    all_results.append(r)

    creators_path.write_text(json.dumps(all_results, indent=2, ensure_ascii=False))

    found_count = sum(1 for r in all_results if r.get("found"))
    print(f"\n  ✓ Creator discovery complete: {found_count}/{len(all_results)} found → {creators_path}")
    return all_results


if __name__ == "__main__":
    week_num = int(sys.argv[1]) if len(sys.argv) > 1 else 9
    print(f"\n{'='*60}\nEVM Creator Discovery — Week {week_num}\n{'='*60}")
    results = discover_creators(week_num)
    found = [r for r in results if r.get("found")]
    print(f"\nFound {len(found)} creator entries:")
    for r in found:
        print(f"  ✅ {r['source_name']}: {r.get('content', {}).get('url', '')[:60]}")
