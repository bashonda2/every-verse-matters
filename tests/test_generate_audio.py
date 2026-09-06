import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from pipeline import generate_audio


class FakeStreamingResponse:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def stream_to_file(self, path):
        Path(path).write_bytes(b"fake mp3")


class AudioGenerationTests(unittest.TestCase):
    def test_production_defaults_use_quality_voice_and_delivery_instructions(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            content_dir = root / "content"
            audio_dir = root / "audio"
            week_dir = content_dir / "week-01"
            week_dir.mkdir(parents=True)
            hook_path = week_dir / "hook.json"
            hook_path.write_text(
                json.dumps({"title": "Week 1", "hook": "A thoughtful opening."})
            )

            captured = {}

            def create(**kwargs):
                captured.update(kwargs)
                return FakeStreamingResponse()

            fake_client = SimpleNamespace(
                audio=SimpleNamespace(
                    speech=SimpleNamespace(
                        with_streaming_response=SimpleNamespace(create=create)
                    )
                )
            )

            with (
                patch.object(generate_audio, "CONTENT_DIR", content_dir),
                patch.object(generate_audio, "AUDIO_DIR", audio_dir),
                patch.dict(
                    generate_audio.os.environ,
                    {"OPENAI_API_KEY": "test-key"},
                ),
                patch("openai.OpenAI", return_value=fake_client),
            ):
                output = generate_audio.generate_audio(1)

            self.assertTrue(output.exists())
            self.assertEqual(captured["model"], "gpt-4o-mini-tts")
            self.assertEqual(captured["voice"], "cedar")
            self.assertIn("warm, natural", captured["instructions"])

            hook = json.loads(hook_path.read_text())
            self.assertEqual(hook["audio_voice"], "cedar")
            self.assertEqual(hook["audio_model"], "gpt-4o-mini-tts")
            self.assertEqual(hook["audio_url"], "/audio/week-01-hook.mp3")


if __name__ == "__main__":
    unittest.main()
