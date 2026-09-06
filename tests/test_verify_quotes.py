import unittest
from types import SimpleNamespace

from pipeline.verify_quotes import quote_in_registry, verify_with_web_search


class QuoteRegistryTests(unittest.TestCase):
    def setUp(self):
        self.registry = {
            "the best is yet to be": {
                "name": "The Best Is Yet to Be",
                "author": "Elder Jeffrey R. Holland",
            },
            "elder jeffrey r. holland": {
                "name": "The Best Is Yet to Be",
                "author": "Elder Jeffrey R. Holland",
            },
        }

    def test_known_speaker_does_not_verify_an_unknown_talk(self):
        quote = {
            "speaker": "Elder Jeffrey R. Holland",
            "talk_title": "A Fabricated Talk",
        }

        self.assertFalse(quote_in_registry(quote, self.registry))

    def test_exact_registered_talk_and_speaker_are_verified(self):
        quote = {
            "speaker": "Jeffrey R. Holland",
            "talk_title": "The Best Is Yet to Be",
        }

        self.assertTrue(quote_in_registry(quote, self.registry))

    def test_unverified_web_result_is_not_misread_as_verified(self):
        client = self.fake_client("UNVERIFIED: no matching official source")

        verified, _ = verify_with_web_search(
            {"speaker": "President Example", "talk_title": "Unknown"},
            client,
            "test-model",
        )

        self.assertFalse(verified)

    def test_affirmative_web_result_is_verified(self):
        client = self.fake_client(
            "VERIFIED: https://www.churchofjesuschrist.org/study/example"
        )

        verified, _ = verify_with_web_search(
            {"speaker": "President Example", "talk_title": "Known"},
            client,
            "test-model",
        )

        self.assertTrue(verified)

    @staticmethod
    def fake_client(text):
        messages = SimpleNamespace(
            create=lambda **kwargs: SimpleNamespace(
                content=[SimpleNamespace(text=text)]
            )
        )
        return SimpleNamespace(messages=messages)


if __name__ == "__main__":
    unittest.main()
