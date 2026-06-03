import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path

from web_evidence_capture.config import config_from_dict, ensure_run_dirs
from web_evidence_capture.snapshot import publish_snapshot


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.previous_cwd = Path.cwd()
        os.chdir(self.tmp.name)
        self.config = config_from_dict(
            {
                "target_url": "https://www.example.org/",
                "case_slug": "example-org",
                "allowed_domains": ["www.example.org"],
                "max_pages": 3,
            }
        )
        self.run_dir = Path("cases/example-org/runs/2026-01-01-1200")
        ensure_run_dirs(self.run_dir)
        (self.run_dir / "manifest" / "package-metadata.json").write_text(
            json.dumps({"target_url": self.config.target_url, "case_slug": self.config.case_slug}),
            encoding="utf-8",
        )
        (self.run_dir / "logs" / "capture.jsonl").write_text('{"message":"captured"}\n', encoding="utf-8")

    def tearDown(self):
        os.chdir(self.previous_cwd)
        self.tmp.cleanup()

    def test_partial_snapshot_writes_status_and_hashes(self):
        result = publish_snapshot(self.config, self.run_dir, "capture")
        snapshot_dir = Path(result["snapshot_dir"])
        self.assertTrue((snapshot_dir / "SNAPSHOT-STATUS.md").exists())
        status = json.loads((snapshot_dir / "manifest" / "snapshot-status.json").read_text(encoding="utf-8"))
        self.assertFalse(status["final"])
        self.assertEqual(status["stage"], "capture")
        self.assertIn("inventory", status["completed_stages"])
        self.assertFalse((snapshot_dir / "www.example.org-2026-01-01-1200.zip").exists())
        manifest = json.loads((snapshot_dir / "manifest" / "file-manifest.json").read_text(encoding="utf-8"))
        paths = {row["path"] for row in manifest}
        self.assertNotIn("manifest/file-manifest.json", paths)
        self.assertNotIn("hashes/files.sha256", paths)
        self.assertEqual((snapshot_dir.parent / "latest.txt").read_text(encoding="utf-8"), "2026-01-01-1200\n")

    def add_html_artifacts(self):
        mirror = self.run_dir / "artifacts" / "mirror"
        rendered = self.run_dir / "artifacts" / "rendered-mirror"
        singlefile = self.run_dir / "artifacts" / "singlefile"
        mirror.mkdir(parents=True)
        rendered.mkdir(parents=True)
        singlefile.mkdir(parents=True)
        (mirror / "index.html").write_text("<h1>Static</h1>", encoding="utf-8")
        (rendered / "index.html").write_text(
            (
                '<h1>Rendered</h1>'
                '<a href="/about-us/">About</a>'
                '<a href="/missing/">Missing</a>'
                '<a href="https://external.example/">External</a>'
                '<a class="dropdown-toggle" href="#">Menu</a>'
                '<button aria-label="Toggle navigation"></button>'
                '<a href="/about-us/"><button>About button</button></a>'
                '<a href="/about-us/">Plain CTA</a><button>Plain CTA</button>'
            ),
            encoding="utf-8",
        )
        (rendered / "about-us").mkdir()
        (rendered / "about-us" / "index.html").write_text("<h1>About</h1><a href='/'>Home</a>", encoding="utf-8")
        (singlefile / "001.singlefile.html").write_text("<h1>SingleFile</h1>", encoding="utf-8")
        (self.run_dir / "manifest" / "render-result.json").write_text(
            json.dumps(
                [
                    {
                        "url": self.config.target_url,
                        "final_url": self.config.target_url,
                        "title": "Home",
                        "rendered_html": "artifacts/rendered-mirror/index.html",
                    },
                    {
                        "url": "https://www.example.org/about-us/",
                        "final_url": "https://www.example.org/about-us/",
                        "title": "About",
                        "rendered_html": "artifacts/rendered-mirror/about-us/index.html",
                    },
                ]
            ),
            encoding="utf-8",
        )
        (self.run_dir / "manifest" / "singlefile-result.json").write_text(
            json.dumps(
                [
                    {
                        "exists": True,
                        "output": str(self.run_dir / "artifacts" / "singlefile" / "001.singlefile.html"),
                        "url": self.config.target_url,
                    }
                ]
            ),
            encoding="utf-8",
        )

    def test_final_snapshot_creates_archives(self):
        self.add_html_artifacts()
        result = publish_snapshot(self.config, self.run_dir, "final", final=True)
        snapshot_dir = Path(result["snapshot_dir"])
        full_zip = snapshot_dir / "www.example.org-2026-01-01-1200.zip"
        website_zip = snapshot_dir / "www.example.org-2026-01-01-1200-website-html.zip"
        self.assertTrue(full_zip.exists())
        self.assertTrue(website_zip.exists())
        with zipfile.ZipFile(full_zip) as archive:
            full_names = set(archive.namelist())
        self.assertIn("hashes/files.sha256", full_names)
        self.assertIn("manifest/file-manifest.json", full_names)
        self.assertIn(website_zip.name, full_names)
        with zipfile.ZipFile(website_zip) as archive:
            names = set(archive.namelist())
            self.assertIn("README.md", names)
            self.assertIn("index.html", names)
            self.assertIn("open-rendered-mirror.html", names)
            self.assertIn("site-map.html", names)
            self.assertIn("rendered-mirror/index.html", names)
            self.assertIn("rendered-mirror/_site-map.html", names)
            placeholder_names = [name for name in names if name.startswith("rendered-mirror/_not-captured/")]
            self.assertEqual(len(placeholder_names), 1)
            rendered_index = archive.read("rendered-mirror/index.html").decode("utf-8")
        self.assertIn('href="about-us/index.html"', rendered_index)
        self.assertIn('href="_not-captured/', rendered_index)
        self.assertIn('href="https://external.example/"', rendered_index)
        self.assertIn('data-web-evidence-offline-helper="1"', rendered_index)
        self.assertIn("button.closest('a[href]')", rendered_index)
        self.assertIn("findLinkByLabel(buttonLabel)", rendered_index)
        self.assertIn("openSiteMap(event)", rendered_index)
        archives = json.loads((snapshot_dir / "manifest" / "snapshot-archives.json").read_text(encoding="utf-8"))
        self.assertEqual(archives["complete_snapshot_zip"], full_zip.name)
        self.assertEqual(archives["website_html_zip"], website_zip.name)
        self.assertTrue(archives["complete_snapshot_zip_committed_to_snapshot"])
        self.assertTrue(archives["website_html_zip_committed_to_snapshot"])

    def test_large_final_archives_move_outside_git_snapshot(self):
        self.add_html_artifacts()
        result = publish_snapshot(self.config, self.run_dir, "final", final=True, max_git_archive_bytes=1)
        snapshot_dir = Path(result["snapshot_dir"])
        full_zip_name = "www.example.org-2026-01-01-1200.zip"
        website_zip_name = "www.example.org-2026-01-01-1200-website-html.zip"
        self.assertFalse((snapshot_dir / full_zip_name).exists())
        self.assertFalse((snapshot_dir / website_zip_name).exists())
        external_dir = Path("snapshot-archives/www.example.org/2026-01-01-1200")
        self.assertTrue((external_dir / full_zip_name).exists())
        self.assertTrue((external_dir / website_zip_name).exists())
        self.assertTrue((snapshot_dir / "ARCHIVES.md").exists())
        start_here = (snapshot_dir / "START-HERE.md").read_text(encoding="utf-8")
        self.assertIn("Archive Download Details", start_here)
        archives = json.loads((snapshot_dir / "manifest" / "snapshot-archives.json").read_text(encoding="utf-8"))
        self.assertFalse(archives["complete_snapshot_zip_committed_to_snapshot"])
        self.assertFalse(archives["website_html_zip_committed_to_snapshot"])
        self.assertIn("snapshot-archives/www.example.org/2026-01-01-1200", archives["complete_snapshot_zip_external_path"])
        manifest = json.loads((snapshot_dir / "manifest" / "file-manifest.json").read_text(encoding="utf-8"))
        paths = {row["path"] for row in manifest}
        self.assertNotIn(full_zip_name, paths)
        self.assertNotIn(website_zip_name, paths)


if __name__ == "__main__":
    unittest.main()
