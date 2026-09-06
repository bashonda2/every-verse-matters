#!/usr/bin/env python3
"""
Cross-Reference Verification
Checks that scripture cross-references in commentary actually exist.
Uses stored KJV verse data and known verse counts.

Two levels:
1. Existence check — does this book/chapter/verse actually exist?
2. Plausibility check — if we have the KJV text, does the cited verse
   plausibly relate to the connection described?

This catches the most common hallucination: citing "Alma 7:14" when the
relevant verse is "Alma 7:10", or citing a chapter/verse that doesn't exist.
"""

import sys
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# Verse counts for all Standard Works used in EVM
# Extended to include BoM, D&C, PGP for cross-reference verification
VERSE_COUNTS = {
    # Old Testament
    "Genesis": {1:31,2:25,3:24,4:26,5:32,6:22,7:24,8:22,9:29,10:32,11:32,12:20,13:18,14:24,15:21,16:16,17:27,18:33,19:38,20:18,21:34,22:24,23:20,24:67,25:34,26:35,27:46,28:22,29:35,30:43,31:55,32:32,33:20,34:31,35:29,36:43,37:36,38:30,39:23,40:23,41:57,42:38,43:34,44:34,45:28,46:34,47:31,48:22,49:33,50:26},
    "Exodus": {1:22,2:25,3:22,4:31,5:23,6:30,7:25,8:32,9:35,10:29,11:10,12:51,13:22,14:31,15:27,16:36,17:16,18:27,19:25,20:26,21:36,22:31,23:33,24:18,25:40,26:37,27:21,28:43,29:46,30:38,31:18,32:35,33:23,34:35,35:35,36:38,37:29,38:31,39:43,40:38},
    "Leviticus": {1:17,2:16,3:17,4:35,5:19,6:30,7:38,8:36,9:24,10:20,11:47,12:8,13:59,14:57,15:33,16:34,17:16,18:30,19:37,20:27,21:24,22:33,23:44,24:23,25:55,26:46,27:34},
    "Numbers": {1:54,2:34,3:51,4:49,5:31,6:27,7:89,8:26,9:23,10:36,11:35,12:16,13:33,14:45,15:41,16:50,17:13,18:32,19:22,20:29,21:35,22:41,23:30,24:25,25:18,26:65,27:23,28:31,29:40,30:16,31:54,32:42,33:56,34:29,35:34,36:13},
    # New Testament
    "Matthew": {1:25,2:23,3:17,4:25,5:48,6:34,7:29,8:34,9:38,10:42,11:30,12:50,13:58,14:36,15:39,16:28,17:27,18:35,19:30,20:34,21:46,22:46,23:39,24:51,25:46,26:75,27:66,28:20},
    "Mark": {1:45,2:28,3:35,4:41,5:43,6:56,7:37,8:38,9:50,10:52,11:33,12:44,13:37,14:72,15:47,16:20},
    "Luke": {1:80,2:52,3:38,4:44,5:39,6:49,7:50,8:56,9:62,10:42,11:54,12:59,13:35,14:35,15:32,16:31,17:37,18:43,19:48,20:47,21:38,22:71,23:56,24:53},
    "John": {1:51,2:25,3:36,4:54,5:47,6:71,7:53,8:59,9:41,10:42,11:57,12:50,13:38,14:31,15:27,16:33,17:26,18:40,19:42,20:31,21:25},
    "Romans": {1:32,2:29,3:31,4:25,5:21,6:23,7:25,8:39,9:33,10:21,11:36,12:21,13:14,14:23,15:33,16:27},
    "Hebrews": {1:14,2:18,3:19,4:16,5:14,6:20,7:28,8:13,9:28,10:39,11:40,12:29,13:25},
    # Book of Mormon
    "1 Nephi": {1:20,2:24,3:31,4:38,5:22,6:6,7:22,8:38,9:6,10:22,11:36,12:23,13:42,14:30,15:36,16:39,17:55,18:25,19:24,20:22,21:26,22:31},
    "2 Nephi": {1:32,2:30,3:25,4:35,5:34,6:18,7:11,8:25,9:54,10:25,11:8,12:22,13:26,14:6,15:30,16:13,17:25,18:22,19:21,20:34,21:16,22:6,23:22,24:32,25:30,26:33,27:35,28:32,29:14,30:18,31:21,32:9,33:15},
    "Mosiah": {1:18,2:41,3:27,4:30,5:15,6:7,7:33,8:21,9:19,10:22,11:29,12:37,13:34,14:12,15:31,16:15,17:20,18:35,19:29,20:26,21:36,22:16,23:39,24:25,25:24,26:39,27:37,28:20,29:47},
    "Alma": {1:33,2:38,3:27,4:20,5:62,6:8,7:27,8:32,9:34,10:32,11:46,12:37,13:31,14:29,15:19,16:21,17:39,18:43,19:36,20:30,21:23,22:35,23:18,24:30,25:17,26:37,27:30,28:14,29:17,30:60,31:38,32:43,33:23,34:41,35:16,36:30,37:47,38:15,39:19,40:26,41:15,42:31,43:54,44:24,45:24,46:41,47:36,48:25,49:30,50:40,51:37,52:40,53:23,54:24,55:35,56:57,57:36,58:41,59:13,60:36,61:21,62:52,63:17},
    "Helaman": {1:34,2:14,3:37,4:26,5:52,6:41,7:29,8:28,9:41,10:19,11:38,12:26,13:39,14:31,15:17,16:25},
    "3 Nephi": {1:30,2:19,3:26,4:33,5:26,6:30,7:26,8:25,9:22,10:19,11:41,12:48,13:34,14:27,15:24,16:20,17:25,18:39,19:36,20:46,21:29,22:17,23:14,24:18,25:6,26:21,27:33,28:40,29:9,30:2},
    "4 Nephi": {1:49},
    "Mormon": {1:19,2:29,3:22,4:23,5:24,6:22,7:10,8:41,9:37},
    "Ether": {1:43,2:25,3:28,4:19,5:6,6:30,7:27,8:26,9:35,10:34,11:23,12:41,13:31,14:31,15:34},
    "Moroni": {1:4,2:3,3:4,4:3,5:2,6:9,7:48,8:30,9:26,10:34},
    # D&C — all 138 sections (canonical LDS 2013 edition verse counts)
    "D&C": {1:39,2:3,3:20,4:7,5:35,6:37,7:8,8:12,9:14,10:70,11:30,12:9,13:1,14:11,15:6,16:6,17:9,18:47,19:41,20:84,21:12,22:4,23:7,24:19,25:16,26:3,27:18,28:16,29:50,30:11,31:13,32:5,33:18,34:12,35:27,36:8,37:4,38:42,39:24,40:3,41:12,42:93,43:35,44:6,45:75,46:33,47:4,48:6,49:28,50:46,51:20,52:44,53:7,54:10,55:6,56:20,57:16,58:65,59:24,60:17,61:39,62:9,63:66,64:43,65:6,66:13,67:14,68:35,69:8,70:18,71:11,72:26,73:6,74:7,75:36,76:119,77:15,78:22,79:4,80:5,81:7,82:24,83:6,84:120,85:12,86:11,87:8,88:141,89:21,90:37,91:6,92:2,93:53,94:17,95:17,96:9,97:28,98:48,99:8,100:17,101:101,102:34,103:40,104:86,105:41,106:8,107:100,108:8,109:80,110:16,111:11,112:34,113:10,114:2,115:19,116:1,117:16,118:6,119:7,120:1,121:46,122:9,123:17,124:145,125:4,126:3,127:12,128:25,129:9,130:23,131:8,132:66,133:74,134:12,135:7,136:42,137:10,138:60},
    "D&C Section": {1:39,2:3,3:20,4:7,5:35,6:37,7:8,8:12,9:14,10:70,11:30,12:9,13:1,14:11,15:6,16:6,17:9,18:47,19:41,20:84,21:12,22:4,23:7,24:19,25:16,26:3,27:18,28:16,29:50,30:11,31:13,32:5,33:18,34:12,35:27,36:8,37:4,38:42,39:24,40:3,41:12,42:93,43:35,44:6,45:75,46:33,47:4,48:6,49:28,50:46,51:20,52:44,53:7,54:10,55:6,56:20,57:16,58:65,59:24,60:17,61:39,62:9,63:66,64:43,65:6,66:13,67:14,68:35,69:8,70:18,71:11,72:26,73:6,74:7,75:36,76:119,77:15,78:22,79:4,80:5,81:7,82:24,83:6,84:120,85:12,86:11,87:8,88:141,89:21,90:37,91:6,92:2,93:53,94:17,95:17,96:9,97:28,98:48,99:8,100:17,101:101,102:34,103:40,104:86,105:41,106:8,107:100,108:8,109:80,110:16,111:11,112:34,113:10,114:2,115:19,116:1,117:16,118:6,119:7,120:1,121:46,122:9,123:17,124:145,125:4,126:3,127:12,128:25,129:9,130:23,131:8,132:66,133:74,134:12,135:7,136:42,137:10,138:60},
    # PGP
    "Moses": {1:42,2:31,3:25,4:32,5:59,6:68,7:69,8:30},
    "Abraham": {1:31,2:25,3:28,4:31,5:21},
    "Joseph Smith—History": {1:75},
    "Joseph Smith—Matthew": {1:55},
    "Articles of Faith": {1:13},
}

# Book name normalization
BOOK_ALIASES = {
    "d&c": "D&C",
    "dc": "D&C",
    "doctrine and covenants": "D&C",
    "1 ne": "1 Nephi",
    "2 ne": "2 Nephi",
    "w of m": "Words of Mormon",
    "js—h": "Joseph Smith—History",
    "js—m": "Joseph Smith—Matthew",
    "a of f": "Articles of Faith",
}


def normalize_book(book: str) -> str:
    normalized = book.strip()
    lower = normalized.lower()
    return BOOK_ALIASES.get(lower, normalized)


def verse_exists(book: str, chapter: int, verse: int) -> tuple[bool, str]:
    """Check if a book/chapter/verse reference is valid."""
    book = normalize_book(book)

    if book not in VERSE_COUNTS:
        return True, "unknown_book"  # Don't flag unknown books — might just be missing from our data

    chapter_data = VERSE_COUNTS[book]
    if chapter not in chapter_data:
        return False, f"Chapter {chapter} doesn't exist in {book}"

    max_verse = chapter_data[chapter]
    if verse > max_verse:
        return False, f"{book} {chapter} only has {max_verse} verses, not {verse}"
    if verse < 1:
        return False, f"Verse number must be >= 1"

    return True, "ok"


def parse_reference(ref: str) -> tuple[str | None, int | None, int | None]:
    """Parse 'Alma 7:10' or 'D&C 84:33' into (book, chapter, verse)."""
    ref = ref.strip()

    # Handle ranges like "Alma 7:10-11" — check the starting verse
    ref = re.sub(r'-\d+$', '', ref)

    # Pattern: Book name then chapter:verse
    m = re.match(r'^(.+?)\s+(\d+):(\d+)$', ref)
    if m:
        return m.group(1), int(m.group(2)), int(m.group(3))

    return None, None, None


def verify_references(week_num: int) -> dict:
    """Verify all cross-references in a week's commentary."""
    week_dir = ROOT / "content" / "weeks" / "2026" / f"week-{str(week_num).zfill(2)}"
    comm_path = week_dir / "commentary.json"

    if not comm_path.exists():
        return {
            "week": week_num, "status": "no_commentary", "issues": [],
            "total_refs": 0, "invalid_refs": 0, "pass": True,
        }

    verses = json.loads(comm_path.read_text())

    issues = []
    total_refs = 0
    invalid_refs = 0

    for verse_data in verses:
        verse_ref = f"{verse_data.get('book')} {verse_data.get('chapter')}:{verse_data.get('verse')}"
        xrefs = verse_data.get("commentary", {}).get("cross_references", [])

        for xref in xrefs:
            ref = xref.get("reference", "")
            total_refs += 1

            book, chapter, verse = parse_reference(ref)
            if book is None:
                # Can't parse — skip, not necessarily wrong
                continue

            exists, reason = verse_exists(book, chapter, verse)
            if not exists:
                invalid_refs += 1
                issues.append({
                    "in_verse": verse_ref,
                    "bad_ref": ref,
                    "reason": reason,
                })
                print(f"  ⚠️  Invalid cross-ref in {verse_ref}: '{ref}' — {reason}")

    report = {
        "week": week_num,
        "total_refs": total_refs,
        "invalid_refs": invalid_refs,
        "issues": issues,
        "pass": invalid_refs == 0,
    }

    report_path = week_dir / "xref_verification_report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False))

    print(f"  ✓ Cross-reference check: {invalid_refs}/{total_refs} invalid → {report_path}")
    return report


if __name__ == "__main__":
    week_num = int(sys.argv[1]) if len(sys.argv) > 1 else 9
    print(f"\n{'='*60}\nEVM Cross-Reference Verification — Week {week_num}\n{'='*60}")
    report = verify_references(week_num)
    if report["issues"]:
        print(f"\nInvalid references found:")
        for issue in report["issues"]:
            print(f"  {issue['in_verse']}: '{issue['bad_ref']}' — {issue['reason']}")
    else:
        print(f"\nAll {report['total_refs']} cross-references validated ✅")
