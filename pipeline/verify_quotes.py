#!/usr/bin/env python3
"""
Stage 4: Quote Verification
Checks all prophetic quotes in the week's commentary against sources_registry.json.
Flags unverifiable quotes and optionally strips them before publish.

Strategy:
1. Load commentary.json for the week
2. For each verse's prophetic_quotes, check speaker+talk_title against registry
3. Use web search to verify quotes not in registry
4. Flag unverifiable — strip from publish copy, log for review

Output: Modifies commentary.json in place + creates quote_verification_report.json
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


def load_registry() -> dict:
    """Build a lookup dict from sources_registry.json for fast quote matching."""
    registry_path = DATA_DIR / "sources_registry.json"
    if not registry_path.exists():
        return {}

    registry = json.loads(registry_path.read_text())
    lookup = {}
    for entry in registry:
        if entry.get("category") in ("prophetic_commentary", "official_church"):
            key = entry.get("name", "").lower()
            lookup[key] = entry
            # Also index by author
            author = entry.get("author", "").lower()
            if author:
                lookup[author] = entry
    return lookup


def quote_in_registry(quote: dict, registry: dict) -> bool:
    """Check if a quote is from a verifiable source in the registry."""
    speaker = quote.get("speaker", "").lower()
    talk = quote.get("talk_title", "").lower()

    for key, entry in registry.items():
        if speaker and speaker in key:
            return True
        if speaker and key in speaker:
            return True
        if talk and talk[:20] in key:
            return True
    return False


def verify_with_web_search(quote: dict, client, model: str) -> tuple[bool, str]:
    """Use web search to verify a quote exists. Returns (verified, url_or_note)."""
    speaker = quote.get("speaker", "")
    talk = quote.get("talk_title", "")
    text = quote.get("quote_or_paraphrase", "")[:100]

    query = f'"{speaker}" "{talk}" site:churchofjesuschrist.org'
    if not talk:
        query = f'"{speaker}" general conference "{text[:50]}"'

    try:
        response = client.messages.create(
            model=model,
            max_tokens=500,
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            system="You verify LDS General Conference quotes. Search and return ONLY 'VERIFIED: [url]' or 'UNVERIFIED: [reason]'. Nothing else.",
            messages=[{"role": "user", "content": f"Verify this quote exists:\nSpeaker: {speaker}\nTalk: {talk}\nText: {text}\n\nSearch: {query}"}],
        )
        text_out = ""
        for block in response.content:
            if hasattr(block, "text"):
                text_out += block.text
        if "VERIFIED" in text_out.upper():
            return True, text_out.strip()
        return False, text_out.strip()
    except Exception as e:
        return False, f"Search error: {e}"


def verify_quotes(week_num: int, strip_unverified: bool = True) -> dict:
    week_dir = CONTENT_DIR / f"week-{str(week_num).zfill(2)}"
    comm_path = week_dir / "commentary.json"

    if not comm_path.exists():
        print(f"  No commentary.json for week {week_num} — nothing to verify")
        return {
            "week": week_num, "status": "no_commentary", "quotes_checked": 0,
            "verified": [], "unverified_stripped": [], "unverified_kept": [],
        }

    verses = json.loads(comm_path.read_text())
    registry = load_registry()
    config = load_config()
    client = get_client()
    model = config.get("discovery_model", "claude-sonnet-4-5-20250929")

    report = {
        "week": week_num,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "quotes_checked": 0,
        "verified": [],
        "unverified_stripped": [],
        "unverified_kept": [],
    }

    modified = False

    for verse in verses:
        c = verse.get("commentary", {})
        quotes = c.get("prophetic_quotes", [])
        if not quotes:
            continue

        verified_quotes = []
        for q in quotes:
            report["quotes_checked"] += 1
            speaker = q.get("speaker", "Unknown")
            talk = q.get("talk_title", "")

            # Check registry first (fast, free)
            if quote_in_registry(q, registry):
                verified_quotes.append(q)
                report["verified"].append({
                    "verse": f"{verse['book']} {verse['chapter']}:{verse['verse']}",
                    "speaker": speaker,
                    "talk": talk,
                    "method": "registry",
                })
                continue

            # Web search verification
            print(f"    Verifying: {speaker} — '{talk[:40]}'...")
            verified, note = verify_with_web_search(q, client, model)

            if verified:
                verified_quotes.append(q)
                report["verified"].append({
                    "verse": f"{verse['book']} {verse['chapter']}:{verse['verse']}",
                    "speaker": speaker,
                    "talk": talk,
                    "method": "web_search",
                    "note": note,
                })
            else:
                entry = {
                    "verse": f"{verse['book']} {verse['chapter']}:{verse['verse']}",
                    "speaker": speaker,
                    "talk": talk,
                    "text": q.get("quote_or_paraphrase", "")[:100],
                    "reason": note,
                }
                if strip_unverified:
                    report["unverified_stripped"].append(entry)
                    modified = True
                    print(f"    ⚠️  Stripped unverifiable quote: {speaker}")
                else:
                    report["unverified_kept"].append(entry)
                    verified_quotes.append(q)

        c["prophetic_quotes"] = verified_quotes

    if modified:
        comm_path.write_text(json.dumps(verses, indent=2, ensure_ascii=False))
        print(f"  ✓ Commentary updated — {len(report['unverified_stripped'])} quotes stripped")

    report_path = week_dir / "quote_verification_report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False))

    total = report["quotes_checked"]
    verified = len(report["verified"])
    stripped = len(report["unverified_stripped"])
    print(f"  ✓ Quote verification: {verified}/{total} verified, {stripped} stripped → {report_path}")

    return report


if __name__ == "__main__":
    week_num = int(sys.argv[1]) if len(sys.argv) > 1 else 9
    keep = "--keep" in sys.argv  # --keep flag preserves unverified quotes

    print(f"\n{'='*60}\nEVM Quote Verification — Week {week_num}\n{'='*60}")
    report = verify_quotes(week_num, strip_unverified=not keep)
    print(f"\nResult: {report['quotes_checked']} checked, "
          f"{len(report['verified'])} verified, "
          f"{len(report['unverified_stripped'])} stripped")
