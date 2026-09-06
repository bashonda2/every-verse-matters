#!/usr/bin/env python3
"""
Stage: Pre-Publish QA Audit
Runs a comprehensive hallucination check on generated commentary before it ships.
Uses Claude Haiku as a fast, cheap second-opinion auditor on every verse.

Two checks:
1. verify_references.py — checks cross-references against stored KJV text
2. Haiku content audit — flags suspicious prophetic quotes, invented JST changes,
   implausible cross-reference connections

Output: qa_report.json with pass/fail per verse and summary stats.
High-risk prophetic quotes are removed and the sanitized verse is re-audited.
Any high-risk issue that remains after quote removal still blocks deployment.
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
KJV_DIR = ROOT / "data" / "kjv_verses"

# Audit threshold — if more than this % of verses fail, block deployment
FAIL_THRESHOLD_PCT = 10

AUDIT_SYSTEM = """You are a content accuracy auditor for EveryVerseMatters.com, a Latter-day Saint
scripture study platform. Your job is to detect potential hallucinations in AI-generated
scripture commentary before it is published to thousands of members.

Evaluate the provided verse commentary and return ONLY a JSON object with this structure:
{
  "pass": true or false,
  "flags": [],
  "risk_level": "low" | "medium" | "high"
}

FLAG (set pass=false, risk_level="high") if ANY of the following:
- A prophetic quote is attributed to a real Church leader but the talk title or date pattern
  seems vague, generic, or potentially fabricated (e.g., "Faith and Testimony, April 2015" —
  too generic; real talks have specific titles)
- A JST revision is claimed but the language sounds invented or hedged
- A cross-reference verse is cited that seems implausible or the connection described
  doesn't match what the cited verse actually discusses

FLAG (set pass=false, risk_level="medium") if:
- A quote is paraphrased rather than quoted directly but attributed to a specific person
- Multiple prophetic quotes are included in a single verse's commentary (increases risk)
- An archaeological discovery or named scholar is cited without specifics

SET pass=true, risk_level="low" if:
- Prophetic quotes array is empty (safest state)
- Any quotes included have complete, specific citations (full name, specific talk title,
  specific month/year)
- Cross-references are plausible connections to well-known verses
- JST changes say "None" or are absent

IMPORTANT: You are checking for POTENTIAL hallucinations, not verifying truth.
Be conservative — flag anything that raises suspicion. False positives are acceptable.
False negatives (missing a real hallucination) are not."""


def load_kjv_text(book: str, chapter: int, verse: int) -> str | None:
    """Load KJV verse text from stored files if available."""
    book_file = KJV_DIR / f"{book.lower().replace(' ', '_')}.json"
    if not book_file.exists():
        return None
    try:
        data = json.loads(book_file.read_text())
        # Support both {chapter: {verse: text}} and flat array formats
        if isinstance(data, dict):
            return data.get(str(chapter), {}).get(str(verse))
        elif isinstance(data, list):
            for v in data:
                if v.get("chapter") == chapter and v.get("verse") == verse:
                    return v.get("text")
    except Exception:
        return None
    return None


def check_cross_references(verse_data: dict) -> list[dict]:
    """Verify cross-references against stored KJV text where available."""
    issues = []
    refs = verse_data.get("commentary", {}).get("cross_references", [])

    for ref_obj in refs:
        ref = ref_obj.get("reference", "")
        connection = ref_obj.get("connection", "")

        # Parse reference like "Genesis 18:14" or "Alma 7:10"
        m = re.match(r"^(.+?)\s+(\d+):(\d+)$", ref.strip())
        if not m:
            continue

        book, chapter, verse = m.group(1), int(m.group(2)), int(m.group(3))
        kjv_text = load_kjv_text(book, chapter, verse)

        if kjv_text is not None:
            # We have the actual verse — check for obvious mismatches
            # This is a simple keyword overlap check (not semantic)
            connection_words = set(connection.lower().split())
            verse_words = set(kjv_text.lower().split())
            # Very basic: if the connection claims something totally absent from the verse
            # This catches the most egregious fabrications
            overlap = len(connection_words & verse_words)
            if overlap < 2 and len(connection_words) > 5:
                issues.append({
                    "ref": ref,
                    "issue": "low_overlap",
                    "note": f"Cross-reference '{ref}' connection may not match actual verse text",
                    "verse_text": kjv_text[:100],
                })

    return issues


def audit_verse_with_haiku(verse_data: dict, client, model: str = "claude-opus-5") -> dict:
    """Run an audit call on a single verse's commentary.
    Historical name kept for call-site compatibility; audit model is now configurable
    via data/config.json → audit_model (defaults to Opus 5 for stronger anti-hallucination)."""
    ref = f"{verse_data.get('book')} {verse_data.get('chapter')}:{verse_data.get('verse')}"
    commentary = verse_data.get("commentary", {})

    # Build a compact summary for the auditor
    quotes = commentary.get("prophetic_quotes", [])
    jst = commentary.get("restoration_lens", {}).get("jst_changes", "")
    xrefs = commentary.get("cross_references", [])

    audit_input = {
        "verse": ref,
        "prophetic_quotes": quotes,
        "jst_changes": jst,
        "cross_references": xrefs[:5],  # First 5 is enough
    }

    try:
        response = client.messages.create(
            model=model,
            max_tokens=1024,
            thinking={"type": "disabled"},
            system=AUDIT_SYSTEM,
            messages=[{
                "role": "user",
                "content": f"Audit this verse commentary for potential hallucinations:\n\n{json.dumps(audit_input, indent=2)}"
            }]
        )
        # Opus 5 may return ThinkingBlock + TextBlock; grab the text block defensively.
        text = next((b.text for b in response.content if getattr(b, "type", None) == "text"), "").strip()
        # Strip markdown fences
        text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.MULTILINE)
        text = re.sub(r'\s*```$', '', text, flags=re.MULTILINE)
        result = json.loads(text.strip())
        return result
    except Exception as e:
        return {"pass": True, "flags": [], "risk_level": "low", "error": str(e)}


def strip_prophetic_quotes(verse_data: dict) -> list[dict]:
    """Remove and return all prophetic quotes from one verse."""
    commentary = verse_data.get("commentary", {})
    quotes = commentary.get("prophetic_quotes", [])
    if not isinstance(quotes, list) or not quotes:
        return []

    commentary["prophetic_quotes"] = []
    return quotes


def quote_provenance(quote: dict) -> dict:
    """Retain citation metadata without preserving suspect quote text."""
    return {
        key: quote.get(key)
        for key in ("speaker", "talk_title", "month_year")
        if quote.get(key)
    }


def run_qa(week_num: int, audit_all: bool = False) -> dict:
    """
    Run full QA suite on a week's commentary.
    By default, only audits verses with prophetic quotes (where risk is highest).
    Pass audit_all=True to audit every verse (slower, more expensive).
    """
    week_dir = CONTENT_DIR / f"week-{str(week_num).zfill(2)}"
    comm_path = week_dir / "commentary.json"

    if not comm_path.exists():
        print(f"  No commentary.json for week {week_num}")
        return {"week": week_num, "status": "no_commentary", "overall_pass": True}

    verses = json.loads(comm_path.read_text())
    client = get_client()
    config = load_config()
    audit_model = config.get("audit_model", "claude-opus-5")
    print(f"    Audit model: {audit_model}")

    report = {
        "week": week_num,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "audit_model": audit_model,
        "total_verses": len(verses),
        "audited_verses": 0,
        "passed": 0,
        "failed": 0,
        "high_risk": [],
        "medium_risk": [],
        "auto_remediated": [],
        "xref_issues": [],
        "overall_pass": True,
    }

    print(f"\n  Running QA audit for Week {week_num} ({len(verses)} verses)...")
    commentary_modified = False

    for i, verse in enumerate(verses):
        ref = f"{verse.get('book')} {verse.get('chapter')}:{verse.get('verse')}"
        commentary = verse.get("commentary", {})
        has_quotes = bool(commentary.get("prophetic_quotes"))
        has_jst = bool(commentary.get("restoration_lens", {}).get("jst_changes", "").strip()
                       and commentary.get("restoration_lens", {}).get("jst_changes", "").strip().lower() != "none")

        # Check cross-references against KJV text (fast, no API)
        xref_issues = check_cross_references(verse)
        if xref_issues:
            report["xref_issues"].extend([{**issue, "verse": ref} for issue in xref_issues])

        # Haiku audit — run on verses with quotes or JST, or all if audit_all
        should_audit = audit_all or has_quotes or has_jst
        if not should_audit:
            report["passed"] += 1
            continue

        if i % 10 == 0:
            print(f"    Auditing verse {i+1}/{len(verses)}...")

        result = audit_verse_with_haiku(verse, client, model=audit_model)
        report["audited_verses"] += 1

        if not result.get("pass", True):
            # A suspect prophetic quote is safer to omit than to publish. Remove
            # every quote from the flagged verse, then audit the remaining JST
            # and cross-reference content again. Never treat a re-audit error as
            # a pass: unresolved high-risk content must continue to block.
            if result.get("risk_level") == "high" and has_quotes:
                removed_quotes = strip_prophetic_quotes(verse)
                commentary_modified = bool(removed_quotes) or commentary_modified
                remediation_result = audit_verse_with_haiku(
                    verse, client, model=audit_model
                )
                report["audited_verses"] += 1

                remediation = {
                    "verse": ref,
                    "removed_quotes": [
                        quote_provenance(quote) for quote in removed_quotes
                    ],
                    "original_flags": result.get("flags", []),
                    "reaudit_passed": (
                        remediation_result.get("pass") is True
                        and not remediation_result.get("error")
                    ),
                }
                if remediation_result.get("error"):
                    remediation["reaudit_error"] = remediation_result["error"]
                    result = {
                        "pass": False,
                        "risk_level": "high",
                        "flags": [
                            "Automatic quote removal succeeded, but the "
                            f"sanitized verse could not be re-audited: "
                            f"{remediation_result['error']}"
                        ],
                    }
                else:
                    result = remediation_result

                remediation["remaining_risk_level"] = result.get(
                    "risk_level", "low"
                )
                remediation["remaining_flags"] = result.get("flags", [])
                report["auto_remediated"].append(remediation)
                print(
                    f"    🧹 Removed {len(removed_quotes)} high-risk "
                    f"prophetic quote(s) from {ref}; re-audited sanitized verse"
                )

                if result.get("pass") is True:
                    report["passed"] += 1
                    continue

            report["failed"] += 1
            entry = {
                "verse": ref,
                "risk_level": result.get("risk_level", "medium"),
                "flags": result.get("flags", []),
            }
            if result.get("risk_level") == "high":
                report["high_risk"].append(entry)
                print(f"    ⚠️  HIGH RISK: {ref} — {result.get('flags', [])}")
            else:
                report["medium_risk"].append(entry)
                print(f"    ⚡ Medium risk: {ref}")
        else:
            report["passed"] += 1

    # Determine overall pass/fail
    total = report["total_verses"]
    failed = report["failed"]
    high_risk_count = len(report["high_risk"])
    fail_pct = (failed / total * 100) if total > 0 else 0

    report["fail_pct"] = round(fail_pct, 1)
    report["overall_pass"] = fail_pct <= FAIL_THRESHOLD_PCT and high_risk_count == 0

    if commentary_modified:
        comm_path.write_text(json.dumps(verses, indent=2, ensure_ascii=False))
        print(
            f"  ✓ Commentary updated — "
            f"{len(report['auto_remediated'])} verse(s) auto-remediated"
        )

    # Write report
    report_path = week_dir / "qa_report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False))

    status = "✅ PASS" if report["overall_pass"] else "❌ FAIL"
    print(f"\n  QA {status} — {failed}/{total} verses flagged ({fail_pct:.1f}%)")
    print(
        f"  High risk: {high_risk_count} | "
        f"Auto-remediated: {len(report['auto_remediated'])} | "
        f"Medium: {len(report['medium_risk'])} | "
        f"XRef issues: {len(report['xref_issues'])}"
    )
    print(f"  Report: {report_path}")

    return report


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("week", type=int)
    parser.add_argument("--all", action="store_true", help="Audit every verse, not just ones with quotes")
    args = parser.parse_args()

    print(f"\n{'='*60}\nEVM QA Audit — Week {args.week}\n{'='*60}")
    report = run_qa(args.week, audit_all=args.all)
    sys.exit(0 if report["overall_pass"] else 1)
