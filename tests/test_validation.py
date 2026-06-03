import tempfile
import unittest
from pathlib import Path

from web_evidence_capture.config import config_from_dict
from web_evidence_capture.logging_utils import write_json
from web_evidence_capture.validate import validate_run


class ValidationTests(unittest.TestCase):
    def make_run(self, root: Path) -> None:
        for name in ["manifest", "validation", "hashes", "artifacts/mirror", "artifacts/warc", "artifacts/wacz", "artifacts/screenshots", "artifacts/pdf", "logs"]:
            (root / name).mkdir(parents=True, exist_ok=True)
        body = " ".join(["meaningful visible public page text"] * 10)
        (root / "artifacts" / "mirror" / "index.html").write_text(f"<html><body>{body}</body></html>", encoding="utf-8")
        (root / "artifacts" / "warc" / "example.warc.gz").write_bytes(b"warc")
        (root / "artifacts" / "wacz" / "example.wacz").write_bytes(b"wacz")
        (root / "artifacts" / "screenshots" / "001.png").write_bytes(b"png")
        (root / "artifacts" / "pdf" / "001.pdf").write_bytes(b"pdf")
        write_json(root / "manifest" / "package-metadata.json", {"status": "initialized"})
        write_json(root / "manifest" / "capture-result.json", {"warc_path": "artifacts/warc/example.warc.gz", "captured_pages": [], "downloads": [], "access_policy": {}})
        write_json(root / "manifest" / "wacz-result.json", {"wacz_path": "artifacts/wacz/example.wacz", "validate_exit_code": 0, "pages_detected": 1})
        write_json(root / "manifest" / "render-result.json", [{"url": "https://example.org/", "screenshot": "artifacts/screenshots/001.png", "pdf": "artifacts/pdf/001.pdf", "attempts": [{"attempt": 1, "resolved": True}], "error": ""}])

    def test_validates_complete_synthetic_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_run(root)
            config = config_from_dict({"target_url": "https://example.org/", "case_slug": "example"})
            result = validate_run(config, root)
            self.assertEqual(result["status"], "completed_validated")

    def test_empty_mirror_body_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_run(root)
            (root / "artifacts" / "mirror" / "index.html").write_text("<html><body></body></html>", encoding="utf-8")
            config = config_from_dict({"target_url": "https://example.org/", "case_slug": "example"})
            result = validate_run(config, root)
            self.assertIn("mirror_body_empty_or_too_short", result["failures"])

    def test_rendered_mirror_can_satisfy_meaningful_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_run(root)
            (root / "artifacts" / "mirror" / "index.html").write_text("<html><body></body></html>", encoding="utf-8")
            (root / "artifacts" / "rendered-mirror").mkdir(parents=True, exist_ok=True)
            body = " ".join(["rendered public page body text"] * 10)
            (root / "artifacts" / "rendered-mirror" / "index.html").write_text(f"<html><body>{body}</body></html>", encoding="utf-8")
            config = config_from_dict({"target_url": "https://example.org/", "case_slug": "example"})
            result = validate_run(config, root)
            self.assertNotIn("mirror_body_empty_or_too_short", result["failures"])
            self.assertEqual(result["checks"]["mirror_meaningful_body_source"], "rendered")

    def test_incomplete_wacz_page_index_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_run(root)
            write_json(
                root / "manifest" / "wacz-result.json",
                {
                    "wacz_path": "artifacts/wacz/example.wacz",
                    "validate_exit_code": 0,
                    "pages_detected": 1,
                    "pages_input_count": 2,
                    "invalid_passed_pages_count": 0,
                },
            )
            config = config_from_dict({"target_url": "https://example.org/", "case_slug": "example"})
            result = validate_run(config, root)
            self.assertIn("wacz_page_index_incomplete", result["failures"])


if __name__ == "__main__":
    unittest.main()
