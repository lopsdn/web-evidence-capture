import unittest

from web_evidence_capture.validate import collect_render_retries
from web_evidence_capture.wacz import parse_pages_detected


class WaczAndRetryTests(unittest.TestCase):
    def test_parse_pages_detected(self):
        self.assertEqual(parse_pages_detected("Reading\nNum Pages Detected: 0\nDone"), 0)
        self.assertEqual(parse_pages_detected("Num Pages Detected: 12"), 12)
        self.assertIsNone(parse_pages_detected("No page count here"))

    def test_collect_render_retries(self):
        retries = collect_render_retries(
            [
                {
                    "url": "https://example.org/",
                    "error": "",
                    "attempts": [
                        {"attempt": 1, "error": "timeout", "resolved": False},
                        {"attempt": 2, "error": "", "resolved": True},
                    ],
                }
            ]
        )
        self.assertEqual(len(retries), 1)
        self.assertTrue(retries[0]["resolved"])


if __name__ == "__main__":
    unittest.main()

