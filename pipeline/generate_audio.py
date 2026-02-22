#!/usr/bin/env python3
"""
Stage: Hook Audio Generation
Converts the hook paragraph to speech using OpenAI TTS.
Outputs an MP3 to site/public/audio/week-{nn}-hook.mp3 for static serving.

Requires: OPENAI_API_KEY in .env
Model: tts-1-hd (higher quality), voice: nova (warm, clear)
Cost: ~$15/1M chars. Hook is ~200 words ≈ $0.02/week.
"""

import sys
import json
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent
load_dotenv(ROOT / ".env")

AUDIO_DIR = ROOT / "site" / "public" / "audio"
CONTENT_DIR = ROOT / "content" / "weeks" / "2026"


def generate_audio(week_num: int, voice: str = "nova", model: str = "tts-1-hd") -> Path:
    """Generate TTS audio for a week's hook paragraph."""
    try:
        from openai import OpenAI
    except ImportError:
        print("  openai package not installed. Run: pip install openai")
        sys.exit(1)

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("  OPENAI_API_KEY not set in .env — skipping audio generation")
        sys.exit(1)

    week_dir = CONTENT_DIR / f"week-{str(week_num).zfill(2)}"
    hook_path = week_dir / "hook.json"

    if not hook_path.exists():
        print(f"  No hook.json for week {week_num} — run generate_hooks.py first")
        sys.exit(1)

    hook_data = json.loads(hook_path.read_text())
    hook_text = hook_data.get("hook", "").strip()

    if not hook_text:
        print("  Hook text is empty — nothing to generate")
        sys.exit(1)

    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    output_path = AUDIO_DIR / f"week-{str(week_num).zfill(2)}-hook.mp3"

    print(f"  Generating audio for Week {week_num}: {hook_data.get('title', '')}")
    print(f"  Voice: {voice} | Model: {model}")
    print(f"  Text length: {len(hook_text)} chars")

    client = OpenAI(api_key=api_key)

    with client.audio.speech.with_streaming_response.create(
        model=model,
        voice=voice,
        input=hook_text,
        response_format="mp3",
    ) as response:
        response.stream_to_file(str(output_path))

    size_kb = output_path.stat().st_size / 1024
    cost_estimate = len(hook_text) * 15 / 1_000_000  # tts-1-hd: $15/1M chars
    print(f"  ✓ Audio saved: {output_path} ({size_kb:.0f} KB, ~${cost_estimate:.4f})")

    # Update hook.json with audio path
    hook_data["audio_url"] = f"/audio/week-{str(week_num).zfill(2)}-hook.mp3"
    hook_data["audio_voice"] = voice
    hook_path.write_text(json.dumps(hook_data, indent=2, ensure_ascii=False))
    print(f"  ✓ hook.json updated with audio_url")

    return output_path


if __name__ == "__main__":
    week_num = int(sys.argv[1]) if len(sys.argv) > 1 else 9
    voice = sys.argv[2] if len(sys.argv) > 2 else "nova"

    print(f"\n{'='*60}")
    print(f"EVM Audio Generation — Week {week_num}")
    print(f"{'='*60}\n")

    path = generate_audio(week_num, voice=voice)
    print(f"\nDone. Serve at: /audio/{path.name}")
    print("Rebuild the site to include the audio file: npm run build (in /site)")
