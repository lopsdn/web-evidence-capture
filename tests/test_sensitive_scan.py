import unittest

from web_evidence_capture.sensitive_scan import scan_text


class SensitiveScanTests(unittest.TestCase):
    def test_detects_constructed_bearer_token(self):
        token = "Bearer " + "A" * 24
        findings = scan_text(token)
        self.assertEqual(findings[0]["type"], "bearer_token")

    def test_clean_text_has_no_findings(self):
        self.assertEqual(scan_text("ordinary public report text"), [])


if __name__ == "__main__":
    unittest.main()

