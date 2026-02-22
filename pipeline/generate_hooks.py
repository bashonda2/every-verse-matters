"""
Stage 5: Homepage Hook Paragraph Generation
Generates a compelling opening paragraph for each week's homepage section.
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

SYSTEM_PROMPT = """You are writing the opening hook paragraph for EveryVerseMatters.com's weekly
scripture study page. This paragraph appears on the homepage and must make readers want to
dive deeper into this week's study.

WRITE ONE PARAGRAPH (4-6 sentences) that:
- Opens with something surprising, insightful, or emotionally resonant from the actual content
- Synthesizes the official lesson theme with the deeper scholarly/spiritual insights
- May include ONE verified prophetic quote if it powerfully connects (optional — only if it genuinely elevates the paragraph)
- Ends with a sense of invitation — the reader should feel drawn to study further
- Tone: warm, intelligent, faithful, compelling — like the opening of the best sacrament meeting talk you've ever heard

DO NOT:
- Use generic devotional language ("This week we learn about God's love...")
- Summarize the chapter contents like a textbook
- Include more than one quote
- Sound like AI-generated marketing copy
- Use phrases like "In this week's study" or "This week's reading"

OUTPUT: A single paragraph of natural, compelling prose. No JSON wrapper, no labels — just the paragraph."""


def build_user_message(week_data: dict, commentary: list, overviews: dict) -> str:
    title = week_data["title"]
    scripture_block = week_data["scripture_block"]
    official_url = week_data.get("official_url", "")

    # Pull top insights from commentary — first verse of each chapter + a few standouts
    highlights = []
    chapters_seen = set()
    for verse in commentary:
        ch_key = f"{verse['book']} {verse['chapter']}"
        if ch_key not in chapters_seen:
            chapters_seen.add(ch_key)
            c = verse.get("commentary", {})
            if c.get("narrative"):
                highlights.append(f"{verse['book']} {verse['chapter']}:{verse['verse']} — {c['narrative'][:400]}")

    # Add a few word studies and restoration lens highlights
    extras = []
    for verse in commentary[::20]:  # every 20th verse
        c = verse.get("commentary", {})
        ws = c.get("word_study", [])
        if ws and isinstance(ws, list) and ws[0].get("meaning"):
            extras.append(f"Word study on '{ws[0].get('term_english', '')}': {ws[0].get('meaning', '')[:200]}")
        rl = c.get("restoration_lens", {})
        if isinstance(rl, dict) and rl.get("temple_connections"):
            extras.append(f"Temple connection: {str(rl['temple_connections'])[:200]}")

    highlights_text = "\n".join(highlights[:6])
    extras_text = "\n".join(extras[:3])

    overview_text = ""
    for ch, text in list(overviews.items())[:2]:
        overview_text += f"\n{ch}: {str(text)[:300]}"

    return f"""WEEK: {week_data['week']} — {title}
SCRIPTURE: {scripture_block}
OFFICIAL LESSON: {official_url}

CHAPTER OVERVIEWS:{overview_text}

KEY INSIGHTS FROM COMMENTARY:
{highlights_text}

ADDITIONAL HIGHLIGHTS:
{extras_text}

Write the hook paragraph for this week."""


def generate_hook(week_num: int) -> dict:
    schedule = json.loads((DATA_DIR / "cfm_schedule.json").read_text())
    week_data = next((w for w in schedule if w["week"] == week_num), None)
    if not week_data:
        raise ValueError(f"Week {week_num} not found in schedule")

    week_dir = CONTENT_DIR / f"week-{str(week_num).padStart if hasattr(str(week_num), 'padStart') else str(week_num).zfill(2)}"
    week_dir = CONTENT_DIR / f"week-{str(week_num).zfill(2)}"

    comm_path = week_dir / "commentary.json"
    if not comm_path.exists():
        raise FileNotFoundError(f"No commentary found for week {week_num} at {comm_path}")

    commentary = json.loads(comm_path.read_text())
    overviews_path = week_dir / "chapter_overviews.json"
    overviews = json.loads(overviews_path.read_text()) if overviews_path.exists() else {}

    print(f"  Generating hook for Week {week_num}: {week_data['title']}...")
    user_message = build_user_message(week_data, commentary, overviews)

    config = load_config()
    result = call_claude(
        system_prompt=SYSTEM_PROMPT,
        user_message=user_message,
        model="claude-sonnet-4-5-20250929",
        max_tokens=500,
    )

    hook_text = result["text"].strip()
    # Strip any accidental JSON or label wrapping
    hook_text = re.sub(r'^(hook|paragraph|output)[:\s]*', '', hook_text, flags=re.IGNORECASE).strip()
    hook_text = hook_text.strip('"').strip()

    output = {
        "week": week_num,
        "title": week_data["title"],
        "scripture_block": week_data["scripture_block"],
        "hook": hook_text,
        "generated_by": result["usage"]["model"],
        "usage": result["usage"],
    }

    out_path = week_dir / "hook.json"
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False))

    tokens = result["usage"]
    cost = (tokens["input_tokens"] * 3 + tokens["output_tokens"] * 15) / 1_000_000
    print(f"  ✓ Hook generated ({tokens['input_tokens']} in / {tokens['output_tokens']} out, ${cost:.4f}) → {out_path}")
    return output


if __name__ == "__main__":
    week_num = int(sys.argv[1]) if len(sys.argv) > 1 else 9
    print(f"\n{'='*60}")
    print(f"EVM Hook Generation — Week {week_num}")
    print(f"{'='*60}\n")
    result = generate_hook(week_num)
    print(f"\nHook paragraph:\n\n{result['hook']}\n")
