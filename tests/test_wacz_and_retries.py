import unittest
import tempfile
import zipfile
from pathlib import Path

from web_evidence_capture.validate import collect_render_retries
from web_evidence_capture.config import CaptureConfig
from web_evidence_capture.logging_utils import write_json
from web_evidence_capture.wacz import build_pages_jsonl, count_wacz_pages, parse_pages_detected


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

    def test_build_pages_jsonl_from_capture_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "manifest").mkdir()
            write_json(
                root / "manifest" / "capture-result.json",
                {
                    "captured_pages": [
                        {"url": "https://example.org/", "final_url": "https://example.org/", "title": "Home"},
                        {"url": "https://example.org/about", "final_url": "https://example.org/about", "title": "About"},
                    ]
                },
            )
            write_json(
                root / "manifest" / "render-result.json",
                [{"url": "https://example.org/about", "final_url": "https://example.org/about", "title": "Rendered About"}],
            )
            config = CaptureConfig(target_url="https://example.org/", case_slug="example", allowed_domains=["example.org"])

            result = build_pages_jsonl(config, root)

            self.assertEqual(result["count"], 2)
            text = (root / result["path"]).read_text(encoding="utf-8")
            self.assertIn('"format": "json-pages-1.0"', text)
            self.assertIn('"seed": true', text)
            self.assertIn("Rendered About", text)

    def test_count_wacz_pages(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "example.wacz"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("pages/pages.jsonl", '{"format":"json-pages-1.0","id":"pages"}\n{"url":"https://example.org/","ts":"2026-06-03T00:00:00Z"}\n')

            self.assertEqual(count_wacz_pages(path), 1)


if __name__ == "__main__":
    unittest.main()
