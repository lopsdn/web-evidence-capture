import unittest
import tempfile
from pathlib import Path

from web_evidence_capture.sensitive_scan import scan_product_tree, scan_text, scan_tree


class SensitiveScanTests(unittest.TestCase):
    def test_detects_constructed_bearer_token(self):
        token = "Bearer " + "A" * 24
        findings = scan_text(token)
        self.assertEqual(findings[0]["type"], "bearer_token")

    def test_clean_text_has_no_findings(self):
        self.assertEqual(scan_text("ordinary public report text"), [])

    def test_product_scan_excludes_captured_snapshots(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "snapshots" / "example").mkdir(parents=True)
            (root / "snapshots" / "example" / "network-events.jsonl").write_text(
                "Authorization: Bearer " + ("A" * 24),
                encoding="utf-8",
            )
            (root / "src").mkdir()
            self.assertTrue(scan_tree(root))
            self.assertEqual(scan_product_tree(root), [])


if __name__ == "__main__":
    unittest.main()
