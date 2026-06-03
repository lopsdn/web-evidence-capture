import tempfile
import unittest
from pathlib import Path

from web_evidence_capture.hashing import hash_files, write_hashes


class HashingTests(unittest.TestCase):
    def test_hash_excludes_generated_hash_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "manifest").mkdir()
            (root / "hashes").mkdir()
            (root / "artifact.txt").write_text("hello", encoding="utf-8")
            (root / "manifest" / "file-manifest.json").write_text("{}", encoding="utf-8")
            (root / "hashes" / "files.sha256").write_text("placeholder", encoding="utf-8")
            rows = hash_files(root)
            self.assertEqual([row["path"] for row in rows], ["artifact.txt"])
            write_hashes(root)
            rows_after = hash_files(root)
            self.assertEqual([row["path"] for row in rows_after], ["artifact.txt"])


if __name__ == "__main__":
    unittest.main()

