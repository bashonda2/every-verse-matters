#!/usr/bin/env python3
"""
EVM Master Pipeline Orchestrator
Runs all stages in sequence for a given week. Called by cron every Saturday.

Usage:
  python3 pipeline/run_pipeline.py            # auto-detects next week
  python3 pipeline/run_pipeline.py 10         # explicit week number
  python3 pipeline/run_pipeline.py --dry-run  # show what would run, don't execute
"""

import sys
import json
import subprocess
import argparse
import smtplib
import traceback
from datetime import datetime, timezone
from pathlib import Path
from email.mime.text import MIMEText

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))


def load_schedule():
    return json.loads((ROOT / "data" / "cfm_schedule.json").read_text())


def detect_next_week() -> int:
    """Find the upcoming week — the one that starts next or soonest after today."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    schedule = load_schedule()
    # Find the next week that hasn't ended yet
    upcoming = [w for w in schedule if w["date_end"] >= today]
    if not upcoming:
        return schedule[-1]["week"]
    # Prefer the week that starts next (pipeline runs a week ahead)
    future = [w for w in upcoming if w["date_start"] > today]
    if future:
        return future[0]["week"]
    return upcoming[0]["week"]


def week_has_content(week_num: int) -> bool:
    week_dir = ROOT / "content" / "weeks" / "2026" / f"week-{str(week_num).zfill(2)}"
    return (week_dir / "commentary.json").exists()


def run_stage(name: str, script: str, args: list[str], dry_run: bool) -> dict:
    """Run a pipeline stage script and return result dict."""
    print(f"\n{'='*60}")
    print(f"  STAGE: {name}")
    print(f"  Command: python3 {script} {' '.join(args)}")
    print(f"{'='*60}")

    if dry_run:
        print("  [DRY RUN — skipping]")
        return {"stage": name, "status": "dry_run", "elapsed": 0}

    start = datetime.now()
    try:
        result = subprocess.run(
            [sys.executable, str(ROOT / script)] + args,
            capture_output=False,  # stream output live
            text=True,
        )
        elapsed = (datetime.now() - start).total_seconds()
        status = "success" if result.returncode == 0 else "failed"
        return {"stage": name, "status": status, "elapsed": round(elapsed, 1), "returncode": result.returncode}
    except Exception as e:
        elapsed = (datetime.now() - start).total_seconds()
        print(f"  ERROR: {e}")
        return {"stage": name, "status": "error", "elapsed": round(elapsed, 1), "error": str(e)}


def build_and_deploy(dry_run: bool) -> dict:
    """Run the Astro build and rsync to VPS."""
    print(f"\n{'='*60}")
    print(f"  STAGE: Build & Deploy")
    print(f"{'='*60}")

    if dry_run:
        print("  [DRY RUN — skipping]")
        return {"stage": "build_deploy", "status": "dry_run", "elapsed": 0}

    start = datetime.now()
    site_dir = ROOT / "site"

    try:
        # Build
        print("  Building Astro site...")
        r = subprocess.run(["npm", "run", "build"], cwd=site_dir, capture_output=False)
        if r.returncode != 0:
            return {"stage": "build_deploy", "status": "build_failed", "elapsed": 0}

        # Deploy — rsync dist to VPS
        print("  Deploying to VPS...")
        dist = str(site_dir / "dist") + "/"
        r2 = subprocess.run([
            "rsync", "-az", "--delete",
            dist,
            "root@209.74.80.143:/var/www/evm/site/dist/"
        ], capture_output=False)

        elapsed = (datetime.now() - start).total_seconds()
        status = "success" if r2.returncode == 0 else "deploy_failed"
        return {"stage": "build_deploy", "status": status, "elapsed": round(elapsed, 1)}
    except Exception as e:
        return {"stage": "build_deploy", "status": "error", "error": str(e), "elapsed": 0}


def send_notification(week_num: int, results: list[dict], dry_run: bool):
    """Send email summary to Aaron."""
    try:
        config = json.loads((ROOT / "data" / "config.json").read_text())
        email = config.get("notification_email", "")
        if not email or dry_run:
            return

        successes = sum(1 for r in results if r["status"] == "success")
        failures = sum(1 for r in results if r["status"] in ("failed", "error"))
        total_elapsed = sum(r.get("elapsed", 0) for r in results)

        subject = f"EVM Pipeline Week {week_num} — {'✅ SUCCESS' if failures == 0 else '⚠️ PARTIAL FAILURE'}"
        body_lines = [
            f"EVM Pipeline — Week {week_num}",
            f"Run completed: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
            f"Stages: {successes} succeeded, {failures} failed",
            f"Total time: {round(total_elapsed/60, 1)} minutes",
            "",
            "Stage Results:",
        ]
        for r in results:
            icon = "✅" if r["status"] == "success" else "❌"
            body_lines.append(f"  {icon} {r['stage']} — {r['status']} ({r.get('elapsed', 0)}s)")

        body = "\n".join(body_lines)
        print(f"\n📧 Notification would be sent to {email}")
        print(body)

    except Exception as e:
        print(f"  Notification failed: {e}")


def main():
    parser = argparse.ArgumentParser(description="EVM Pipeline Orchestrator")
    parser.add_argument("week", nargs="?", type=int, help="Week number (default: auto-detect)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would run without executing")
    parser.add_argument("--skip-commentary", action="store_true", help="Skip Stage 1 if commentary already exists")
    args = parser.parse_args()

    week_num = args.week or detect_next_week()
    dry_run = args.dry_run

    schedule = load_schedule()
    week_data = next((w for w in schedule if w["week"] == week_num), None)
    if not week_data:
        print(f"ERROR: Week {week_num} not found in schedule")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"  EVM PIPELINE — Week {week_num}: {week_data['title']}")
    print(f"  Scripture: {week_data['scripture_block']}")
    print(f"  Dates: {week_data['date_start']} — {week_data['date_end']}")
    print(f"  Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    print(f"  Started: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*60}")

    results = []
    week_str = str(week_num)

    # Stage 1: Commentary (skip if exists and --skip-commentary)
    if args.skip_commentary and week_has_content(week_num):
        print(f"\n  Skipping Stage 1 — commentary already exists for Week {week_num}")
        results.append({"stage": "commentary", "status": "skipped", "elapsed": 0})
    else:
        r = run_stage("Commentary Generation", "pipeline/generate_commentary.py", [week_str], dry_run)
        results.append(r)
        if r["status"] in ("failed", "error"):
            print("\n  ❌ Stage 1 failed — aborting pipeline")
            send_notification(week_num, results, dry_run)
            sys.exit(1)

    # Stage 2: Creator Discovery
    try:
        from pipeline.discover_creators import discover_creators
        print(f"\n{'='*60}\n  STAGE: Creator Discovery\n{'='*60}")
        if not dry_run:
            discover_creators(week_num)
        results.append({"stage": "creator_discovery", "status": "dry_run" if dry_run else "success", "elapsed": 0})
    except ImportError:
        print("\n  discover_creators.py not found — skipping")
        results.append({"stage": "creator_discovery", "status": "skipped", "elapsed": 0})

    # Stage 3: URL Verification
    try:
        from pipeline.verify_and_check import verify_and_check
        print(f"\n{'='*60}\n  STAGE: URL Verification\n{'='*60}")
        if not dry_run:
            verify_and_check(week_num)
        results.append({"stage": "url_verification", "status": "dry_run" if dry_run else "success", "elapsed": 0})
    except ImportError:
        results.append({"stage": "url_verification", "status": "skipped", "elapsed": 0})

    # Stage 4: Quote Verification
    try:
        from pipeline.verify_quotes import verify_quotes
        print(f"\n{'='*60}\n  STAGE: Quote Verification\n{'='*60}")
        if not dry_run:
            verify_quotes(week_num)
        results.append({"stage": "quote_verification", "status": "dry_run" if dry_run else "success", "elapsed": 0})
    except ImportError:
        results.append({"stage": "quote_verification", "status": "skipped", "elapsed": 0})

    # Stage 5: Hook Generation
    r = run_stage("Hook Generation", "pipeline/generate_hooks.py", [week_str], dry_run)
    results.append(r)

    # Stage 6: Snippet Extraction
    r = run_stage("Snippet Extraction", "pipeline/generate_snippets.py", [week_str], dry_run)
    results.append(r)

    # Stage 7: Build & Deploy
    r = build_and_deploy(dry_run)
    results.append(r)

    # Summary
    print(f"\n{'='*60}")
    print(f"  PIPELINE COMPLETE — Week {week_num}")
    successes = sum(1 for r in results if r["status"] == "success")
    failures = sum(1 for r in results if r["status"] in ("failed", "error"))
    total_elapsed = sum(r.get("elapsed", 0) for r in results)
    print(f"  {successes} stages succeeded | {failures} failed | {round(total_elapsed/60, 1)} min total")
    print(f"{'='*60}\n")

    for r in results:
        icon = "✅" if r["status"] in ("success", "dry_run", "skipped") else "❌"
        print(f"  {icon} {r['stage']}: {r['status']} ({r.get('elapsed', 0)}s)")

    send_notification(week_num, results, dry_run)

    if failures > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
