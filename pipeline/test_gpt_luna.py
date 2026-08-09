#!/usr/bin/env python3
"""
GPT-5.6-Luna Migration Test Harness
====================================
Generates commentary for a single chapter using OpenAI's gpt-5.6-luna model,
using the SAME system prompt, batching, and TCR context injection as the
production Anthropic pipeline. Output is written to logs/gpt-test/ so it can
be compared side-by-side with the Haiku baseline in content/weeks/.

Default target: Job 19 (Week 33). Chosen because it contains the "I know that
my Redeemer liveth" passage (vv.25-27) — the highest-signal Christological
test in the OT — and has full TCR data for Hebrew word-study parity.

Usage:
    python3 pipeline/test_gpt_luna.py                  # Job 19, default
    python3 pipeline/test_gpt_luna.py --book "Job" --chapter 19
    python3 pipeline/test_gpt_luna.py --model gpt-5.6-luna
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from openai import OpenAI
from dotenv import load_dotenv

from pipeline.generate_commentary import (
    load_tcr_chapter,
    format_tcr_context,
    get_verse_count,
    VERSES_PER_BATCH,
)
from pipeline.utils.json_parser import validate_verse_commentary

load_dotenv()


def call_luna(client, model, system_prompt, user_message, max_output_tokens=32000):
    """Call gpt-5.6-luna via Chat Completions with JSON object response format."""
    start = time.time()
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        response_format={"type": "json_object"},
        max_completion_tokens=max_output_tokens,
    )
    elapsed = time.time() - start

    text = resp.choices[0].message.content
    usage = {
        "input_tokens": resp.usage.prompt_tokens,
        "output_tokens": resp.usage.completion_tokens,
        "total_tokens": resp.usage.total_tokens,
        "model": model,
        "elapsed_seconds": round(elapsed, 2),
        "finish_reason": resp.choices[0].finish_reason,
    }
    return {"text": text, "usage": usage}


def build_user_message(book, chapter, v_start, v_end, week_title, week_num, scripture_block, tcr_chapter):
    """Build the per-batch user message — mirrors generate_verse_batch, but tells the
    model to wrap its verse array in {"verses": [...]} so response_format=json_object accepts it."""
    tcr_context = format_tcr_context(tcr_chapter, v_start, v_end)
    return (
        f"Generate verse-by-verse commentary for {book} chapter {chapter}, "
        f"verses {v_start} through {v_end}. "
        f"This is Week {week_num} of Come, Follow Me 2026: '{week_title}'. "
        f"The full week's reading is {scripture_block}. "
        f"Cover every verse from {v_start} to {v_end}. "
        f"Follow the commentary structure exactly.\n\n"
        f"IMPORTANT OUTPUT FORMAT: Return a JSON object with a single key 'verses' "
        f"whose value is the array of verse commentary objects. "
        f"Example: {{\"verses\": [<verse objects following the schema>]}}"
        + tcr_context
    )


def extract_verses(text):
    """gpt-5.6-luna returns a JSON object; unwrap the 'verses' key."""
    data = json.loads(text)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("verses", "commentary", "data", "results"):
            if key in data and isinstance(data[key], list):
                return data[key]
        # Single-verse object fallback
        if "verse" in data and "commentary" in data:
            return [data]
    raise ValueError(f"Unexpected JSON shape: keys={list(data.keys()) if isinstance(data, dict) else type(data)}")


def run(book, chapter, week_num, week_title, scripture_block, model, out_dir):
    system_prompt = (ROOT / "pipeline" / "prompts" / "commentary_system.txt").read_text()
    total_verses = get_verse_count(book, chapter)
    tcr_chapter = load_tcr_chapter(book, chapter)

    print(f"\n{'='*70}")
    print(f"GPT-5.6-Luna Test :: {book} {chapter} ({total_verses} verses)")
    print(f"Model: {model}")
    print(f"TCR context: {'available' if tcr_chapter else 'none'}")
    print(f"Week {week_num}: {week_title}")
    print('='*70)

    client = OpenAI()

    all_verses = []
    all_usage = []
    batch_errors = []
    run_start = time.time()

    v = 1
    while v <= total_verses:
        v_end = min(v + VERSES_PER_BATCH - 1, total_verses)
        print(f"\n  Batch {book} {chapter}:{v}-{v_end}...")
        try:
            user_msg = build_user_message(
                book, chapter, v, v_end, week_title, week_num, scripture_block, tcr_chapter
            )
            result = call_luna(client, model, system_prompt, user_msg)
            u = result["usage"]
            print(
                f"    {u['input_tokens']} in / {u['output_tokens']} out "
                f"in {u['elapsed_seconds']}s [finish: {u['finish_reason']}]"
            )
            verses = extract_verses(result["text"])
            all_verses.extend(verses)
            all_usage.append(u)
        except Exception as e:
            err = f"{book} {chapter}:{v}-{v_end}: {type(e).__name__}: {e}"
            print(f"    BATCH ERROR: {err}")
            batch_errors.append(err)
            # dump raw for post-mortem
            debug_dir = out_dir / "raw_errors"
            debug_dir.mkdir(parents=True, exist_ok=True)
            if 'result' in locals() and result.get("text"):
                (debug_dir / f"{book}_{chapter}_{v}-{v_end}.txt").write_text(result["text"])
        v = v_end + 1

    total_elapsed = round(time.time() - run_start, 2)

    validation_issues = 0
    for verse in all_verses:
        if validate_verse_commentary(verse):
            validation_issues += 1

    summary = {
        "test": "gpt-5.6-luna-migration",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "model": model,
        "target": {"book": book, "chapter": chapter, "week": week_num, "week_title": week_title},
        "totals": {
            "verses_generated": len(all_verses),
            "verses_expected": total_verses,
            "validation_issues": validation_issues,
            "batch_errors": len(batch_errors),
            "input_tokens": sum(u["input_tokens"] for u in all_usage),
            "output_tokens": sum(u["output_tokens"] for u in all_usage),
            "total_tokens": sum(u["total_tokens"] for u in all_usage),
            "elapsed_seconds": total_elapsed,
        },
        "batches": all_usage,
        "errors": batch_errors,
    }

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    slug = f"{book.lower().replace(' ','-')}-{chapter}"
    commentary_path = out_dir / f"{slug}_luna_{ts}.json"
    summary_path = out_dir / f"{slug}_luna_{ts}_summary.json"

    commentary_path.write_text(json.dumps(all_verses, indent=2))
    summary_path.write_text(json.dumps(summary, indent=2))

    print(f"\n{'='*70}")
    print("TEST COMPLETE")
    print('='*70)
    print(f"Verses:            {len(all_verses)} / {total_verses}")
    print(f"Validation issues: {validation_issues}")
    print(f"Batch errors:      {len(batch_errors)}")
    print(f"Input tokens:      {summary['totals']['input_tokens']:,}")
    print(f"Output tokens:     {summary['totals']['output_tokens']:,}")
    print(f"Elapsed:           {total_elapsed}s")
    print(f"\nCommentary: {commentary_path.relative_to(ROOT)}")
    print(f"Summary:    {summary_path.relative_to(ROOT)}")
    return commentary_path, summary_path, all_verses


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--book", default="Job")
    p.add_argument("--chapter", type=int, default=19)
    p.add_argument("--week", type=int, default=33)
    p.add_argument("--week-title", default="Job")
    p.add_argument(
        "--scripture",
        default="Job 1-3; 12-14; 19; 21-24; 38-40; 42",
        help="Full week scripture block for prompt context",
    )
    p.add_argument("--model", default="gpt-5.6-luna")
    p.add_argument("--out-dir", default="logs/gpt-test")
    args = p.parse_args()

    if not os.environ.get("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY not set in environment or .env", file=sys.stderr)
        sys.exit(1)

    out_dir = ROOT / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    run(
        book=args.book,
        chapter=args.chapter,
        week_num=args.week,
        week_title=args.week_title,
        scripture_block=args.scripture,
        model=args.model,
        out_dir=out_dir,
    )


if __name__ == "__main__":
    main()
