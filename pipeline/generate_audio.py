#!/usr/bin/env python3
"""
Stage: Hook Audio Generation
Converts the hook paragraph to speech using OpenAI TTS.
Outputs an MP3 to site/public/audio/week-{nn}-hook.mp3 for static serving.

Requires: OPENAI_API_KEY in .env
Model: gpt-4o-mini-tts, voice: cedar (OpenAI-recommended quality voice)
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
DEFAULT_MODEL = "gpt-4o-mini-tts"
DEFAULT_VOICE = "cedar"
DEFAULT_INSTRUCTIONS = (
    "Speak in a warm, natural, thoughtful voice suited to a scripture study "
    "podcast. Use gentle pacing, clear phrasing, and quiet confidence. Avoid "
    "a synthetic announcer cadence, exaggerated drama, or sales-like energy."
)


def generate_audio(
    week_num: int,
    voice: str = DEFAULT_VOICE,
    model: str = DEFAULT_MODEL,
    instructions: str = DEFAULT_INSTRUCTIONS,
) -> Path:
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

    speech_options = {
        "model": model,
        "voice": voice,
        "input": hook_text,
        "response_format": "mp3",
    }
    # Delivery instructions are supported by the GPT-4o mini TTS family, but
    # not by the legacy tts-1/tts-1-hd models accepted by the CLI override.
    if model.startswith("gpt-4o-mini-tts"):
        speech_options["instructions"] = instructions

    with client.audio.speech.with_streaming_response.create(
        **speech_options,
    ) as response:
        response.stream_to_file(str(output_path))

    size_kb = output_path.stat().st_size / 1024
    print(f"  ✓ Audio saved: {output_path} ({size_kb:.0f} KB)")

    # Update hook.json with audio path
    hook_data["audio_url"] = f"/audio/week-{str(week_num).zfill(2)}-hook.mp3"
    hook_data["audio_voice"] = voice
    hook_data["audio_model"] = model
    hook_path.write_text(json.dumps(hook_data, indent=2, ensure_ascii=False))
    print(f"  ✓ hook.json updated with audio_url")

    return output_path


if __name__ == "__main__":
    week_num = int(sys.argv[1]) if len(sys.argv) > 1 else 9
    voice = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_VOICE
    model = sys.argv[3] if len(sys.argv) > 3 else DEFAULT_MODEL

    print(f"\n{'='*60}")
    print(f"EVM Audio Generation — Week {week_num}")
    print(f"{'='*60}\n")

    path = generate_audio(week_num, voice=voice, model=model)
    print(f"\nDone. Serve at: /audio/{path.name}")
    print("Rebuild the site to include the audio file: npm run build (in /site)")
