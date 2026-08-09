#!/usr/bin/env python3
"""
Claude Model Test Harness
=========================
Mirrors test_gpt_luna.py but for Anthropic models. Generates commentary for a
single chapter using any Claude model (e.g. claude-opus-5), using the SAME
system prompt, batching, and TCR context injection as the production pipeline.
Output goes to logs/claude-test/ for side-by-side comparison with the Haiku 4.5
baseline in content/weeks/.

Default target: Job 19 (Week 33), same as the GPT tests.

Usage:
    python3 pipeline/test_claude_model.py                       # Opus 5, Job 19
    python3 pipeline/test_claude_model.py --model claude-opus-5
    python3 pipeline/test_claude_model.py --book "Job" --chapter 19
"""

import sys
import json
import time
import argparse
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.generate_commentary import (
    load_tcr_chapter,
    format_tcr_context,
    get_verse_count,
    VERSES_PER_BATCH,
)
from pipeline.utils.api_client import call_claude
from pipeline.utils.json_parser import extract_json, validate_verse_commentary
from pipeline.utils.cost_tracker import estimate_cost


def run(book, chapter, week_num, week_title, scripture_block, model, out_dir):
    system_prompt = (ROOT / "pipeline" / "prompts" / "commentary_system.txt").read_text()
    total_verses = get_verse_count(book, chapter)
    tcr_chapter = load_tcr_chapter(book, chapter)

    print(f"\n{'='*70}")
    print(f"Claude Model Test :: {book} {chapter} ({total_verses} verses)")
    print(f"Model: {model}")
    print(f"TCR context: {'available' if tcr_chapter else 'none'}")
    print(f"Week {week_num}: {week_title}")
    print('='*70)

    all_verses = []
    all_usage = []
    batch_errors = []
    run_start = time.time()

    v = 1
    while v <= total_verses:
        v_end = min(v + VERSES_PER_BATCH - 1, total_verses)
        tcr_context = format_tcr_context(tcr_chapter, v, v_end)
        user_msg = (
            f"Generate verse-by-verse commentary for {book} chapter {chapter}, "
            f"verses {v} through {v_end}. "
            f"This is Week {week_num} of Come, Follow Me 2026: '{week_title}'. "
            f"The full week's reading is {scripture_block}. "
            f"Cover every verse from {v} to {v_end}. "
            f"Follow the commentary structure exactly."
            + tcr_context
        )
        print(f"\n  Batch {book} {chapter}:{v}-{v_end}...")
        try:
            result = call_claude(
                system_prompt=system_prompt,
                user_message=user_msg,
                model=model,
                max_tokens=32000,
            )
            u = result["usage"]
            cost = estimate_cost(u)
            print(
                f"    {u['input_tokens']} in / {u['output_tokens']} out "
                f"(${cost:.4f}) in {u['elapsed_seconds']}s [stop: {u['stop_reason']}]"
            )
            verses = extract_json(result["text"])
            if isinstance(verses, dict):
                verses = [verses]
            all_verses.extend(verses)
            all_usage.append(u)
        except Exception as e:
            err = f"{book} {chapter}:{v}-{v_end}: {type(e).__name__}: {e}"
            print(f"    BATCH ERROR: {err}")
            batch_errors.append(err)
        v = v_end + 1

    total_elapsed = round(time.time() - run_start, 2)

    validation_issues = 0
    for verse in all_verses:
        if validate_verse_commentary(verse):
            validation_issues += 1

    total_input = sum(u["input_tokens"] for u in all_usage)
    total_output = sum(u["output_tokens"] for u in all_usage)
    total_cost = sum(estimate_cost(u) for u in all_usage)

    summary = {
        "test": "claude-model-comparison",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "model": model,
        "target": {"book": book, "chapter": chapter, "week": week_num, "week_title": week_title},
        "totals": {
            "verses_generated": len(all_verses),
            "verses_expected": total_verses,
            "validation_issues": validation_issues,
            "batch_errors": len(batch_errors),
            "input_tokens": total_input,
            "output_tokens": total_output,
            "estimated_cost_usd": round(total_cost, 4),
            "elapsed_seconds": total_elapsed,
        },
        "batches": all_usage,
        "errors": batch_errors,
    }

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    model_slug = model.replace("claude-", "").replace(".", "-")
    slug = f"{book.lower().replace(' ','-')}-{chapter}_{model_slug}_{ts}"
    commentary_path = out_dir / f"{slug}.json"
    summary_path = out_dir / f"{slug}_summary.json"
    commentary_path.write_text(json.dumps(all_verses, indent=2))
    summary_path.write_text(json.dumps(summary, indent=2))

    print(f"\n{'='*70}")
    print("TEST COMPLETE")
    print('='*70)
    print(f"Verses:            {len(all_verses)} / {total_verses}")
    print(f"Validation issues: {validation_issues}")
    print(f"Batch errors:      {len(batch_errors)}")
    print(f"Input tokens:      {total_input:,}")
    print(f"Output tokens:     {total_output:,}")
    print(f"Estimated cost:    ${total_cost:.4f}")
    print(f"Elapsed:           {total_elapsed}s")
    print(f"\nCommentary: {commentary_path.relative_to(ROOT)}")
    print(f"Summary:    {summary_path.relative_to(ROOT)}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--book", default="Job")
    p.add_argument("--chapter", type=int, default=19)
    p.add_argument("--week", type=int, default=33)
    p.add_argument("--week-title", default="Job")
    p.add_argument("--scripture", default="Job 1-3; 12-14; 19; 21-24; 38-40; 42")
    p.add_argument("--model", default="claude-opus-5")
    p.add_argument("--out-dir", default="logs/claude-test")
    args = p.parse_args()

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
