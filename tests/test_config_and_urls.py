import unittest

from web_evidence_capture.config import config_from_dict, normalize_allowed_domains, slugify
from web_evidence_capture.mirror import is_private_path, normalize_url, same_domain


class ConfigAndUrlTests(unittest.TestCase):
    def test_allowed_domains_default_www_pair(self):
        self.assertEqual(normalize_allowed_domains("https://example.org/", None), ["example.org", "www.example.org"])

    def test_slugify(self):
        self.assertEqual(slugify("Example Org!"), "example-org")

    def test_config_from_dict_normalizes_domains(self):
        config = config_from_dict({"target_url": "https://www.example.org/", "case_slug": "Example"})
        self.assertEqual(config.case_slug, "example")
        self.assertIn("example.org", config.allowed_domains)

    def test_normalize_url_removes_fragment(self):
        self.assertEqual(normalize_url("/path#section", "https://example.org/"), "https://example.org/path")

    def test_same_domain(self):
        self.assertTrue(same_domain("https://www.example.org/path", ["www.example.org"]))
        self.assertFalse(same_domain("https://other.example/path", ["www.example.org"]))

    def test_private_path(self):
        self.assertTrue(is_private_path("https://example.org/login", [r"/login\b"]))
        self.assertFalse(is_private_path("https://example.org/blog", [r"/login\b"]))


if __name__ == "__main__":
    unittest.main()

