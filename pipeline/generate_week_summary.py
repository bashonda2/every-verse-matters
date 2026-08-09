#!/usr/bin/env python3
"""
Stage: Week Summary Generation
For weeks without full verse-by-verse commentary, generates a rich week-level
summary: hook paragraph, thematic overview, key insights, and highlights for
the homepage two-column layout.

Used for: backfill of past weeks, and as a lighter alternative when full
commentary hasn't run yet.

Output: content/weeks/2026/week-{nn}/week_summary.json
"""

import sys
import json
import re
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.utils.api_client import call_claude
from pipeline.utils.cost_tracker import estimate_cost

CONTENT_DIR = ROOT / "content" / "weeks" / "2026"
DATA_DIR = ROOT / "data"

SYSTEM_PROMPT = """You are the content engine for EveryVerseMatters.com, a Latter-day Saint
scripture study platform. You generate rich, faithful, scholarly week-level summaries of
Come, Follow Me scripture blocks for adult members.

Your voice: the best Institute teacher you ever had — someone who knows Hebrew,
has walked the Holy Land, can quote General Conference from memory, but keeps it
accessible and makes you lean forward. Not devotional fluff. Not academic jargon.

QUALITY STANDARDS:
- Every sentence teaches something specific
- Properly grounded in scripture and Restoration context
- Faithful, faith-affirming — honest about hard questions without undermining testimony
- Accessible to educated adult members (35+), not seminary students
- Cross-references the Restoration: JST revisions, BoM parallels, temple connections"""


def build_prompt(week_data: dict) -> str:
    week = week_data["week"]
    title = week_data["title"]
    scripture = week_data["scripture_block"]
    dates = f"{week_data['date_start']} to {week_data['date_end']}"
    official_url = week_data.get("official_url", "")

    chapters = week_data.get("chapters", [])
    chapter_list = ", ".join(f"{c['book']} {c['chapter']}" for c in chapters)

    return f"""Generate a comprehensive week summary for Come, Follow Me Week {week}: "{title}"
Scripture Block: {scripture}
Chapters: {chapter_list}
Dates: {dates}
Official Lesson: {official_url}

OUTPUT VALID JSON with exactly this structure:

{{
  "hook": "string — 4-6 sentence opening paragraph. Opens with something surprising or emotionally resonant from this specific scripture block. NOT a dry summary. The opening 30 seconds of the best Gospel Doctrine teacher's lesson. May reference one specific verse or moment. Ends with an invitation to study further.",

  "overview": "string — 4-5 paragraphs of substantive narrative overview. Cover: (1) the narrative arc of the scripture block, (2) the central theological theme and why it matters, (3) key Hebrew or linguistic insights if relevant, (4) Restoration connections — JST, BoM parallels, temple, D&C, (5) how these chapters connect to Christ. Write each paragraph as 3-5 sentences of flowing prose.",

  "themes": ["array of 3-5 one-phrase theme titles, e.g. 'Covenant Faithfulness Under Pressure'"],

  "key_verses": [
    {{
      "reference": "e.g. Genesis 22:8",
      "text_kjv": "exact KJV text of the verse",
      "insight": "2-3 sentence explanation of why this verse is significant — what it reveals, what members often miss"
    }}
  ],

  "highlights": [
    {{
      "category": "one of: hebrew_insight | cross_reference | historical_context | restoration_lens | application | prophetic",
      "verse_reference": "e.g. Genesis 18:12",
      "deep_dive_anchor": "url-safe anchor, e.g. genesis-18-12",
      "snippet_text": "2-3 compelling sentences. Should be surprising, specific, and self-contained. This appears as a teaser on the homepage. Make it a 'wait, really?' insight.",
      "label": "display label matching category (Hebrew / Cross-Ref / Historical / Restoration / Application / Prophetic)"
    }}
  ],

  "restoration_lens": "string — 2-3 paragraphs specifically on how the Restoration illuminates this week's content: JST changes, Book of Mormon parallels, D&C connections, temple ordinance connections, prophetic commentary from modern prophets.",

  "application": "string — 2-3 paragraphs on what these chapters mean for modern covenant members. Specific, not generic. What does a Gospel Doctrine teacher, a struggling parent, a returned missionary each take from this week?"
}}

REQUIREMENTS:
- Include exactly 5-6 highlights, covering at least 3 different categories
- Include exactly 3-5 key_verses
- All prophetic quotes must be real and verifiable — if uncertain, omit
- No fabricated attributions. Prefer original analysis over quotes if unsure.
- Return ONLY valid JSON, no markdown fences, no commentary outside the JSON"""


def generate_week_summary(week_num: int) -> dict:
    schedule = json.loads((DATA_DIR / "cfm_schedule.json").read_text())
    week_data = next((w for w in schedule if w["week"] == week_num), None)
    if not week_data:
        raise ValueError(f"Week {week_num} not found")

    week_dir = CONTENT_DIR / f"week-{str(week_num).zfill(2)}"
    week_dir.mkdir(parents=True, exist_ok=True)

    # Skip if full commentary already exists (don't overwrite)
    if (week_dir / "commentary.json").exists():
        print(f"  Week {week_num} already has full commentary — skipping summary generation")
        print(f"  (Run generate_hooks.py and generate_snippets.py instead)")
        return {}

    print(f"\n  Generating summary for Week {week_num}: {week_data['title']}")
    print(f"  Scripture: {week_data['scripture_block']}")

    prompt = build_prompt(week_data)

    result = call_claude(
        system_prompt=SYSTEM_PROMPT,
        user_message=prompt,
        model="claude-sonnet-5",
        max_tokens=5500,
    )

    raw = result["text"].strip()
    # Strip markdown fences if present
    raw = re.sub(r'^```(?:json)?\s*', '', raw, flags=re.MULTILINE)
    raw = re.sub(r'\s*```$', '', raw, flags=re.MULTILINE)
    raw = raw.strip()

    summary_data = json.loads(raw)

    output = {
        "week": week_num,
        "title": week_data["title"],
        "scripture_block": week_data["scripture_block"],
        "date_start": week_data["date_start"],
        "date_end": week_data["date_end"],
        "official_url": week_data.get("official_url", ""),
        "generated_by": result["usage"]["model"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "usage": result["usage"],
        **summary_data,
    }

    out_path = week_dir / "week_summary.json"
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False))

    tokens = result["usage"]
    cost = (tokens["input_tokens"] * 3 + tokens["output_tokens"] * 15) / 1_000_000
    print(f"  ✓ Summary saved ({tokens['input_tokens']} in / {tokens['output_tokens']} out, ${cost:.4f}) → {out_path}")

    # Auto-generate hook.json from summary so generate_audio can use it
    hook_path = week_dir / "hook.json"
    if not hook_path.exists() and summary_data.get("hook"):
        hook_out = {
            "week": week_num,
            "title": week_data["title"],
            "scripture_block": week_data["scripture_block"],
            "hook": summary_data["hook"],
            "generated_by": result["usage"]["model"],
            "usage": {"input_tokens": 0, "output_tokens": 0},
        }
        hook_path.write_text(json.dumps(hook_out, indent=2, ensure_ascii=False))
        print(f"  ✓ hook.json written from summary")

    # Auto-generate snippets.json from highlights so homepage works immediately
    snippets_path = week_dir / "snippets.json"
    if not snippets_path.exists() and summary_data.get("highlights"):
        snippets_out = {
            "week": week_num,
            "title": week_data["title"],
            "scripture_block": week_data["scripture_block"],
            "snippets": summary_data["highlights"],
            "generated_by": result["usage"]["model"],
        }
        snippets_path.write_text(json.dumps(snippets_out, indent=2, ensure_ascii=False))
        print(f"  ✓ snippets.json written from highlights")

    return output


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("weeks", nargs="*", type=int,
                        help="Week numbers to generate (default: 1-8)")
    parser.add_argument("--force", action="store_true",
                        help="Regenerate even if week_summary.json already exists")
    args = parser.parse_args()

    weeks_to_run = args.weeks if args.weeks else list(range(1, 9))

    print(f"\n{'='*60}")
    print(f"EVM Week Summary Generation")
    print(f"Weeks: {weeks_to_run}")
    print(f"{'='*60}")

    total_cost = 0.0
    successes = 0

    for wk in weeks_to_run:
        week_dir = CONTENT_DIR / f"week-{str(wk).zfill(2)}"
        if not args.force and (week_dir / "week_summary.json").exists():
            print(f"\n  Week {wk}: already has week_summary.json — skipping (use --force to regenerate)")
            continue
        try:
            out = generate_week_summary(wk)
            if out:
                cost = (out["usage"]["input_tokens"] * 3 + out["usage"]["output_tokens"] * 15) / 1_000_000
                total_cost += cost
                successes += 1
        except Exception as e:
            print(f"\n  ❌ Week {wk} failed: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n{'='*60}")
    print(f"Complete: {successes}/{len(weeks_to_run)} weeks")
    print(f"Total estimated cost: ${total_cost:.4f}")
    print(f"{'='*60}")
    print(f"\nNext: run generate_audio.py for each week to add voice narration")
    print(f"Then: npm run build (in /site) and rsync to VPS")
