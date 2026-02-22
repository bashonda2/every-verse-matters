"""
Stage 6: Companion Snippet Extraction
Extracts 5-7 compelling insights from the Deep Dive commentary
for display in the homepage two-column layout.
"""

import json
import sys
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from pipeline.utils.api_client import call_claude, load_config

ROOT = Path(__file__).parent.parent
CONTENT_DIR = ROOT / "content" / "weeks" / "2026"
DATA_DIR = ROOT / "data"

SYSTEM_PROMPT = """You are selecting the most compelling insights from EveryVerseMatters.com's
Deep Dive commentary to display as companion snippets on the homepage.

SELECT 6 SNIPPETS that are:
- Surprising ("Did you know the Hebrew word for 'laugh' is the root of Isaac's name?")
- Practically useful for modern gospel living
- Scholarly but accessible (Ancient Near Eastern context, Hebrew wordplays, etc.)
- Cross-reference connections that illuminate (Book of Mormon parallels, D&C connections)
- Restoration-specific insights (JST changes, temple connections)
- Emotionally resonant — the kind of thing that makes a member say "wait, I never knew that"

AVOID:
- Generic statements that could apply to any scripture week
- Anything that sounds like a devotional platitude
- Repeating the same type of insight multiple times

FOR EACH SNIPPET, OUTPUT VALID JSON with these exact fields:
- snippet_text: 2-3 sentences, compelling and self-contained. Should work as a standalone teaser.
- verse_reference: Specific verse (e.g., "Genesis 22:14")
- deep_dive_anchor: URL-safe anchor (e.g., "genesis-22-14")
- category: One of exactly: hebrew_insight, cross_reference, historical_context, restoration_lens, application, prophetic, creator_highlight

OUTPUT: A JSON array of exactly 6 snippet objects. Nothing else — no preamble, no explanation."""


def build_user_message(week_data: dict, commentary: list, overviews: dict) -> str:
    title = week_data["title"]
    scripture_block = week_data["scripture_block"]

    # Build a condensed digest of the commentary for Claude to select from
    digest_parts = []
    for verse in commentary:
        c = verse.get("commentary", {})
        ref = f"{verse['book']} {verse['chapter']}:{verse['verse']}"
        anchor = f"{verse['book'].lower()}-{verse['chapter']}-{verse['verse']}"

        parts = []
        if c.get("narrative"):
            parts.append(f"Narrative: {c['narrative'][:300]}")

        ws = c.get("word_study", [])
        if ws and isinstance(ws, list) and ws[0].get("meaning"):
            w = ws[0]
            parts.append(f"Word study ({w.get('term_english', '')} / {w.get('term_original', '')}): {w.get('meaning', '')[:200]}")

        rl = c.get("restoration_lens", {})
        if isinstance(rl, dict):
            if rl.get("jst_changes") and str(rl["jst_changes"]).strip() not in ("None", "none", "N/A", ""):
                parts.append(f"JST: {str(rl['jst_changes'])[:150]}")
            if rl.get("temple_connections") and str(rl["temple_connections"]).strip() not in ("None", "none", "N/A", ""):
                parts.append(f"Temple: {str(rl['temple_connections'])[:150]}")

        xrefs = c.get("cross_references", [])
        if xrefs and isinstance(xrefs, list) and xrefs[0].get("connection"):
            parts.append(f"Cross-ref ({xrefs[0].get('reference', '')}): {xrefs[0].get('connection', '')[:150]}")

        if parts:
            digest_parts.append(f"[{ref} | anchor: {anchor}]\n" + "\n".join(parts))

    digest = "\n\n".join(digest_parts[:60])  # cap to avoid token overflow

    return f"""WEEK {week_data['week']}: {title}
SCRIPTURE: {scripture_block}

COMMENTARY DIGEST (select your 6 snippets from this):
{digest}

Extract the 6 best snippets. Return only the JSON array."""


def generate_snippets(week_num: int) -> list:
    schedule = json.loads((DATA_DIR / "cfm_schedule.json").read_text())
    week_data = next((w for w in schedule if w["week"] == week_num), None)
    if not week_data:
        raise ValueError(f"Week {week_num} not found in schedule")

    week_dir = CONTENT_DIR / f"week-{str(week_num).zfill(2)}"
    comm_path = week_dir / "commentary.json"
    if not comm_path.exists():
        raise FileNotFoundError(f"No commentary found for week {week_num}")

    commentary = json.loads(comm_path.read_text())
    overviews_path = week_dir / "chapter_overviews.json"
    overviews = json.loads(overviews_path.read_text()) if overviews_path.exists() else {}

    print(f"  Extracting snippets for Week {week_num}: {week_data['title']}...")
    user_message = build_user_message(week_data, commentary, overviews)

    result = call_claude(
        system_prompt=SYSTEM_PROMPT,
        user_message=user_message,
        model="claude-haiku-4-5-20251001",
        max_tokens=2000,
    )

    raw = result["text"].strip()

    # Parse JSON — strip markdown fences if present
    raw = re.sub(r'^```json\s*', '', raw, flags=re.MULTILINE)
    raw = re.sub(r'^```\s*', '', raw, flags=re.MULTILINE)
    raw = raw.strip()

    snippets = json.loads(raw)
    if not isinstance(snippets, list):
        raise ValueError(f"Expected JSON array, got: {type(snippets)}")

    output = {
        "week": week_num,
        "title": week_data["title"],
        "scripture_block": week_data["scripture_block"],
        "snippets": snippets,
        "generated_by": result["usage"]["model"],
        "usage": result["usage"],
    }

    out_path = week_dir / "snippets.json"
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False))

    tokens = result["usage"]
    cost = (tokens["input_tokens"] * 0.80 + tokens["output_tokens"] * 4) / 1_000_000
    print(f"  ✓ {len(snippets)} snippets extracted ({tokens['input_tokens']} in / {tokens['output_tokens']} out, ${cost:.4f}) → {out_path}")
    return snippets


if __name__ == "__main__":
    week_num = int(sys.argv[1]) if len(sys.argv) > 1 else 9
    print(f"\n{'='*60}")
    print(f"EVM Snippet Extraction — Week {week_num}")
    print(f"{'='*60}\n")
    snippets = generate_snippets(week_num)
    print(f"\nSnippets:\n")
    for i, s in enumerate(snippets, 1):
        print(f"{i}. [{s.get('category', '?')}] {s.get('verse_reference', '?')}")
        print(f"   {s.get('snippet_text', '')[:120]}...")
        print()
