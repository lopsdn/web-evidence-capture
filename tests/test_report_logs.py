import tempfile
import unittest
from pathlib import Path

from web_evidence_capture.report import write_tool_log_summary


class ReportLogTests(unittest.TestCase):
    def test_tool_log_summary_indexes_jsonl_logs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            log_root = root / "logs"
            log_root.mkdir(parents=True)
            (log_root / "render.log").write_text(
                '{"timestamp_utc":"2026-06-03T14:00:00Z","message":"start","error":""}\n'
                '{"timestamp_utc":"2026-06-03T14:01:00Z","message":"rendered","error":""}\n',
                encoding="utf-8",
            )

            write_tool_log_summary(root)

            summary = (log_root / "tool-log-summary.md").read_text(encoding="utf-8")
            self.assertIn("render.log", summary)
            self.assertIn("2", summary)
            self.assertIn("start, rendered", summary)


if __name__ == "__main__":
    unittest.main()
