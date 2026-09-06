import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from pipeline import run_qa


class QaAutoRemediationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.content_dir = Path(self.temp_dir.name)
        self.week_dir = self.content_dir / "week-01"
        self.week_dir.mkdir()
        self.commentary_path = self.week_dir / "commentary.json"
        self.commentary_path.write_text(
            json.dumps(
                [
                    {
                        "book": "Genesis",
                        "chapter": 1,
                        "verse": 1,
                        "commentary": {
                            "prophetic_quotes": [
                                {
                                    "speaker": "President Example",
                                    "talk_title": "A Fabricated Talk",
                                    "month_year": "April 2026",
                                    "quote": "Suspect text",
                                }
                            ],
                            "cross_references": [],
                            "restoration_lens": {"jst_changes": "None"},
                        },
                    }
                ]
            )
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def run_audit(self, results):
        with (
            patch.object(run_qa, "CONTENT_DIR", self.content_dir),
            patch.object(run_qa, "get_client", return_value=Mock()),
            patch.object(
                run_qa, "load_config", return_value={"audit_model": "test-model"}
            ),
            patch.object(
                run_qa, "audit_verse_with_haiku", side_effect=results
            ) as auditor,
        ):
            return run_qa.run_qa(1)

    def test_high_risk_quote_is_removed_and_sanitized_verse_passes(self):
        report = self.run_audit(
            [
                {
                    "pass": False,
                    "risk_level": "high",
                    "flags": ["Potentially fabricated quote"],
                },
                {"pass": True, "risk_level": "low", "flags": []},
            ]
        )

        saved = json.loads(self.commentary_path.read_text())
        self.assertEqual(saved[0]["commentary"]["prophetic_quotes"], [])
        self.assertTrue(report["overall_pass"])
        self.assertEqual(report["failed"], 0)
        self.assertEqual(len(report["auto_remediated"]), 1)
        self.assertTrue(report["auto_remediated"][0]["reaudit_passed"])
        self.assertNotIn(
            "quote", report["auto_remediated"][0]["removed_quotes"][0]
        )

    def test_remaining_high_risk_issue_still_blocks(self):
        report = self.run_audit(
            [
                {
                    "pass": False,
                    "risk_level": "high",
                    "flags": ["Potentially fabricated quote"],
                },
                {
                    "pass": False,
                    "risk_level": "high",
                    "flags": ["Invented JST revision remains"],
                },
            ]
        )

        self.assertFalse(report["overall_pass"])
        self.assertEqual(report["failed"], 1)
        self.assertEqual(len(report["high_risk"]), 1)
        self.assertEqual(
            report["high_risk"][0]["flags"],
            ["Invented JST revision remains"],
        )

    def test_reaudit_error_never_allows_publish(self):
        report = self.run_audit(
            [
                {
                    "pass": False,
                    "risk_level": "high",
                    "flags": ["Potentially fabricated quote"],
                },
                {
                    "pass": True,
                    "risk_level": "low",
                    "flags": [],
                    "error": "API unavailable",
                },
            ]
        )

        self.assertFalse(report["overall_pass"])
        self.assertIn("could not be re-audited", report["high_risk"][0]["flags"][0])


if __name__ == "__main__":
    unittest.main()
