#!/usr/bin/env python3
"""
Stage 1: Commentary Generation
Generates verse-by-verse commentary for a given CFM week using the Claude API.
Chapters are split into batches of ~8 verses to stay within token limits.
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.utils.api_client import call_claude, load_config
from pipeline.utils.json_parser import extract_json, validate_verse_commentary
from pipeline.utils.cost_tracker import log_pipeline_run, estimate_cost

VERSES_PER_BATCH = 6


# Verse counts for OT books used in CFM 2026
VERSE_COUNTS = {
    "Genesis": {
        1:31,2:25,3:24,4:26,5:32,6:22,7:24,8:22,9:29,10:32,
        11:32,12:20,13:18,14:24,15:21,16:16,17:27,18:33,19:38,20:18,
        21:34,22:24,23:20,24:67,25:34,26:35,27:46,28:22,29:35,30:43,
        31:55,32:32,33:20,34:31,35:29,36:43,37:36,38:30,39:23,40:23,
        41:57,42:38,43:34,44:34,45:28,46:34,47:31,48:22,49:33,50:26,
    },
    "Exodus": {
        1:22,2:25,3:22,4:31,5:23,6:30,7:25,8:32,9:35,10:29,
        11:10,12:51,13:22,14:31,15:27,16:36,17:16,18:27,19:25,20:26,
        24:18,31:18,32:35,33:23,34:35,35:35,36:38,37:29,38:31,39:43,40:38,
    },
    "Leviticus": {1:17,4:35,16:34,19:37},
    "Numbers": {
        11:35,12:16,13:33,14:45,20:29,21:35,22:41,23:30,24:25,27:23,
    },
    "Deuteronomy": {6:25,7:26,8:20,15:23,18:22,29:29,30:20,34:12},
    "Joshua": {1:18,2:24,3:17,4:24,5:15,6:27,7:26,8:35,23:16,24:33},
    "Judges": {2:23,3:31,4:24,6:40,7:25,8:35,13:25,14:20,15:20,16:31},
    "Ruth": {1:22,2:23,3:18,4:22},
    "1 Samuel": {
        1:28,2:36,3:21,4:22,5:12,6:21,7:17,8:22,9:27,10:27,
        13:23,15:35,16:23,17:58,18:30,24:22,25:44,26:25,
    },
    "2 Samuel": {5:25,6:23,7:29,11:27,12:31},
    "1 Kings": {3:28,6:38,7:51,8:66,9:28,11:43,12:33,13:34,17:24,18:46,19:21,20:43,21:29,22:53},
    "2 Kings": {2:25,3:27,4:44,5:27,6:33,7:20,16:20,17:41,18:37,19:37,20:21,21:26,22:20,23:37,24:20,25:30},
    "2 Chronicles": {14:15,15:19,16:14,17:19,18:34,19:11,20:37,26:23,30:27},
    "Ezra": {1:11,3:13,4:24,5:17,6:22,7:28},
    "Nehemiah": {2:20,4:23,5:19,6:19,8:18},
    "Esther": {1:22,2:23,3:15,4:17,5:14,6:14,7:10,8:17,9:32,10:3},
    "Job": {1:22,2:13,3:26,12:25,13:28,14:22,19:29,21:34,22:30,23:17,24:25,38:41,39:30,40:24,42:17},
    "Psalms": {
        1:6,2:12,8:9,19:14,20:9,21:13,22:31,23:6,24:10,25:22,
        26:12,27:14,28:9,29:11,30:12,31:24,32:11,33:22,40:17,46:11,
        49:20,50:23,51:19,61:8,62:12,63:11,64:10,65:13,66:20,
        69:36,70:5,71:24,72:20,77:20,78:72,85:13,86:17,
        102:28,103:22,110:7,116:19,117:2,118:29,119:176,
        127:5,128:6,135:21,136:26,137:9,138:8,139:24,
        146:10,147:20,148:14,149:9,150:6,
    },
    "Proverbs": {1:33,2:22,3:35,4:27,15:33,16:33,22:29,31:31},
    "Ecclesiastes": {1:18,2:26,3:22,11:10,12:14},
    "Isaiah": {
        1:31,2:22,3:26,4:6,5:30,6:13,7:25,8:22,9:21,10:34,11:16,12:6,
        13:22,14:32,22:25,24:23,25:12,26:21,27:13,28:29,29:24,30:33,35:10,
        40:31,41:29,42:25,43:28,44:28,45:25,46:13,47:15,48:22,49:26,
        50:11,51:23,52:15,53:12,54:17,55:13,56:12,57:21,
        58:14,59:21,60:22,61:11,62:12,63:19,64:12,65:25,66:24,
    },
    "Jeremiah": {
        1:19,2:37,3:25,7:34,16:21,17:27,18:23,20:18,
        31:40,32:44,33:26,36:32,37:21,38:28,
    },
    "Lamentations": {1:22,3:66},
    "Ezekiel": {1:28,2:10,3:27,33:33,34:31,36:38,37:28,47:23},
    "Daniel": {1:21,2:49,3:30,4:37,5:31,6:28,7:28},
    "Hosea": {1:11,2:23,3:5,4:19,5:15,6:11,10:15,11:12,12:14,13:16,14:9},
    "Joel": {1:20,2:32,3:21},
    "Amos": {1:15,2:16,3:15,4:13,5:27,6:14,7:17,8:14,9:15},
    "Obadiah": {1:21},
    "Jonah": {1:17,2:10,3:10,4:11},
    "Micah": {1:16,2:13,3:12,4:13,5:15,6:16,7:20},
    "Nahum": {1:15,2:13,3:19},
    "Habakkuk": {1:17,2:20,3:19},
    "Zephaniah": {1:18,2:15,3:20},
    "Haggai": {1:15,2:23},
    "Zechariah": {1:21,2:13,3:10,4:14,7:14,8:23,9:17,10:12,11:17,12:14,13:9,14:21},
    "Malachi": {1:14,2:17,3:18,4:6},
    "Moses": {1:42,2:31,3:25,4:32,5:59,6:68,7:69,8:30},
    "Abraham": {1:31,2:25,3:28,4:31,5:21},
}


def get_verse_count(book, chapter):
    book_data = VERSE_COUNTS.get(book, {})
    return book_data.get(chapter, 30)


def load_schedule():
    with open(ROOT / "data" / "cfm_schedule.json") as f:
        return json.load(f)


def load_system_prompt():
    with open(ROOT / "pipeline" / "prompts" / "commentary_system.txt") as f:
        return f.read()


def get_week(week_num, year=2026):
    schedule = load_schedule()
    for week in schedule:
        if week["week"] == week_num and week["year"] == year:
            return week
    raise ValueError(f"Week {week_num} ({year}) not found in schedule")


def load_tcr_chapter(book, chapter):
    """Load The Covenant Rendering (TCR) data for a chapter, if available."""
    slug_map = {
        "Genesis": "genesis",
        "Exodus": "exodus",
        "Leviticus": "leviticus",
        "Numbers": "numbers",
        "Deuteronomy": "deuteronomy",
    }
    slug = slug_map.get(book)
    if not slug:
        return None
    path = ROOT / "content" / "tcr" / slug / f"chapter-{chapter:02d}.json"
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def format_tcr_context(tcr_chapter, verse_start, verse_end):
    """Format TCR verses for the given range into a context block for the prompt."""
    if not tcr_chapter:
        return ""

    chunks = []
    for v in tcr_chapter["verses"]:
        if not (verse_start <= v["verse"] <= verse_end):
            continue

        parts = [
            f"  Verse {v['verse']}:",
            f"    Hebrew (WLC): {v['text_hebrew']}",
            f"    KJV:          {v['text_kjv']}",
            f"    TCR Rendering: {v['rendering']}",
        ]

        if v.get("expanded_rendering"):
            parts.append(f"    Expanded Meaning: {v['expanded_rendering']}")

        if v.get("translator_notes"):
            notes = " | ".join(v["translator_notes"][:3])  # cap at 3 to avoid bloat
            parts.append(f"    Translator Notes: {notes}")

        if v.get("key_terms"):
            for kt in v["key_terms"][:4]:  # cap at 4 key terms
                parts.append(
                    f"    Key Term — {kt['hebrew']} ({kt['transliteration']}) → \"{kt['rendered_as']}\": {kt['note']}"
                )

        chunks.append("\n".join(parts))

    if not chunks:
        return ""

    return (
        "\n\nTHE COVENANT RENDERING (TCR) — SOURCE CONTEXT:\n"
        "The following is a scholarly modern English translation of these verses from the original Hebrew "
        "(Westminster Leningrad Codex), translated by Aaron Blonquist and released under CC-BY-4.0. "
        "Use the TCR rendering, translator notes, and key term definitions to ENRICH your commentary — "
        "especially for Hebrew word studies, theological depth, and translation nuances. "
        "You may reference 'The Covenant Rendering' by name when noting that a word carries deeper Hebrew meaning.\n\n"
        + "\n\n".join(chunks)
    )


def generate_verse_batch(
    book, chapter, verse_start, verse_end,
    week_title, week_num, scripture_block,
    system_prompt, model, tcr_chapter=None,
):
    """Generate commentary for a batch of verses within a chapter."""

    tcr_context = format_tcr_context(tcr_chapter, verse_start, verse_end)

    user_message = (
        f"Generate verse-by-verse commentary for {book} chapter {chapter}, "
        f"verses {verse_start} through {verse_end}. "
        f"This is Week {week_num} of Come, Follow Me 2026: '{week_title}'. "
        f"The full week's reading is {scripture_block}. "
        f"Cover every verse from {verse_start} to {verse_end}. "
        f"Follow the commentary structure exactly."
        + tcr_context
    )

    print(f"    Batch: {book} {chapter}:{verse_start}-{verse_end}...")
    result = call_claude(
        system_prompt=system_prompt,
        user_message=user_message,
        model=model,
        max_tokens=32000,
    )

    usage = result["usage"]
    cost = estimate_cost(usage)
    print(
        f"    Done: {usage['input_tokens']} in / {usage['output_tokens']} out "
        f"(${cost:.4f}) in {usage['elapsed_seconds']}s "
        f"[stop: {usage['stop_reason']}]"
    )

    try:
        verses = extract_json(result["text"])
    except ValueError:
        # Save raw response for debugging
        debug_dir = ROOT / "logs" / "errors"
        debug_dir.mkdir(parents=True, exist_ok=True)
        debug_file = debug_dir / f"{book}_{chapter}_{verse_start}-{verse_end}_raw.txt"
        with open(debug_file, "w") as f:
            f.write(result["text"])
        print(f"    Raw response saved to {debug_file}")
        raise

    if isinstance(verses, dict):
        verses = [verses]

    return verses, usage


def generate_chapter(book, chapter, week_title, week_num, scripture_block, system_prompt, model):
    """Generate commentary for a full chapter by splitting into batches."""
    total_verses = get_verse_count(book, chapter)
    tcr_chapter = load_tcr_chapter(book, chapter)
    if tcr_chapter:
        print(f"  {book} {chapter} ({total_verses} verses) [TCR available ✓]")
    else:
        print(f"  {book} {chapter} ({total_verses} verses)")

    all_verses = []
    all_usage = []
    batch_errors = []

    verse = 1
    while verse <= total_verses:
        batch_end = min(verse + VERSES_PER_BATCH - 1, total_verses)
        try:
            verses, usage = generate_verse_batch(
                book, chapter, verse, batch_end,
                week_title, week_num, scripture_block,
                system_prompt, model, tcr_chapter=tcr_chapter,
            )
            all_verses.extend(verses)
            all_usage.append(usage)
        except Exception as e:
            err = f"{book} {chapter}:{verse}-{batch_end}: {e}"
            print(f"    BATCH ERROR: {err}")
            batch_errors.append(err)
        verse = batch_end + 1

    # Validate
    issues_count = 0
    for v in all_verses:
        problems = validate_verse_commentary(v)
        if problems:
            issues_count += 1
            key = f"{v.get('book', '?')} {v.get('chapter', '?')}:{v.get('verse', '?')}"
            for p in problems:
                print(f"    WARNING: {key}: {p}")

    if issues_count:
        print(f"  {issues_count} verse(s) with validation issues in {book} {chapter}")
    
    print(f"  {book} {chapter} complete: {len(all_verses)} verses, {len(batch_errors)} errors")

    return all_verses, all_usage, batch_errors


def run(week_num, year=2026, chapters=None):
    """Generate commentary for an entire week."""
    week = get_week(week_num, year)
    config = load_config()
    system_prompt = load_system_prompt()
    model = config["commentary_model"]

    target_chapters = chapters or week["chapters"]

    if not target_chapters:
        print(f"No chapters defined for Week {week_num}. Skipping.")
        return

    total_verses = sum(get_verse_count(c["book"], c["chapter"]) for c in target_chapters)
    total_batches = sum(
        -(-get_verse_count(c["book"], c["chapter"]) // VERSES_PER_BATCH)
        for c in target_chapters
    )

    print(f"\n{'='*60}")
    print(f"EVM Commentary Generation — Week {week_num}: {week['title']}")
    print(f"Scripture Block: {week['scripture_block']}")
    print(f"Chapters: {len(target_chapters)} | Verses: ~{total_verses} | Batches: {total_batches}")
    print(f"Model: {model} | Batch size: {VERSES_PER_BATCH} verses")
    print(f"{'='*60}\n")

    all_verses = []
    all_usage = []
    errors = []

    for ch in target_chapters:
        book = ch["book"]
        chapter = ch["chapter"]
        try:
            verses, usage_list, batch_errors = generate_chapter(
                book=book,
                chapter=chapter,
                week_title=week["title"],
                week_num=week_num,
                scripture_block=week["scripture_block"],
                system_prompt=system_prompt,
                model=model,
            )
            all_verses.extend(verses)
            all_usage.extend(usage_list)
            errors.extend(batch_errors)
        except Exception as e:
            error_msg = f"{book} {chapter}: {e}"
            print(f"  CHAPTER ERROR: {error_msg}")
            errors.append(error_msg)

    # Write output
    week_dir = ROOT / "content" / "weeks" / str(year) / f"week-{week_num:02d}"
    week_dir.mkdir(parents=True, exist_ok=True)

    commentary_path = week_dir / "commentary.json"
    with open(commentary_path, "w") as f:
        json.dump(all_verses, f, indent=2, ensure_ascii=False)

    total_cost = sum(estimate_cost(u) for u in all_usage)
    metadata = {
        "week": week_num,
        "year": year,
        "title": week["title"],
        "scripture_block": week["scripture_block"],
        "generated_at": datetime.now().isoformat(),
        "model": model,
        "chapters_requested": len(target_chapters),
        "chapters_completed": len(target_chapters) - len(errors),
        "total_verses": len(all_verses),
        "total_batches": len(all_usage),
        "total_input_tokens": sum(u["input_tokens"] for u in all_usage),
        "total_output_tokens": sum(u["output_tokens"] for u in all_usage),
        "estimated_cost_usd": round(total_cost, 4),
        "errors": errors,
    }
    with open(week_dir / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    status = "success" if not errors else "partial"
    log_pipeline_run(
        week=week_num,
        year=year,
        stage="commentary",
        usage_list=all_usage,
        status=status,
        errors=errors,
        output_path=str(commentary_path),
    )

    print(f"\n{'='*60}")
    print(f"COMPLETE")
    print(f"Verses generated: {len(all_verses)}")
    print(f"API calls: {len(all_usage)}")
    print(f"Estimated cost: ${total_cost:.4f}")
    print(f"Output: {commentary_path}")
    if errors:
        print(f"Errors ({len(errors)}):")
        for e in errors:
            print(f"  - {e}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate EVM commentary for a CFM week")
    parser.add_argument("week", type=int, help="Week number (1-52)")
    parser.add_argument("--year", type=int, default=2026, help="Year (default: 2026)")
    parser.add_argument(
        "--chapter",
        type=str,
        help="Generate a single chapter only, e.g. 'Genesis:18'",
    )
    args = parser.parse_args()

    chapters_override = None
    if args.chapter:
        book, ch = args.chapter.split(":")
        chapters_override = [{"book": book, "chapter": int(ch)}]

    run(args.week, args.year, chapters_override)
