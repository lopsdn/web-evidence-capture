import time
import urllib.robotparser
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Set
from urllib.parse import urljoin

import requests

from .config import CaptureConfig
from .logging_utils import local_now, log_event, utc_now, write_json
from .mirror import LinkExtractor, is_download_url, is_private_path, looks_like_html, normalize_url, same_domain


def build_robot_parser(target_url: str, robots_text: str) -> urllib.robotparser.RobotFileParser:
    parser = urllib.robotparser.RobotFileParser()
    parser.set_url(urljoin(target_url, "/robots.txt"))
    parser.parse(robots_text.splitlines())
    return parser


class InventoryRunner:
    def __init__(self, config: CaptureConfig, run_dir: Path) -> None:
        self.config = config
        self.run_dir = run_dir
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": config.user_agent, "Accept": "*/*"})
        self.last_request_at = 0.0
        self.robot_parser: Optional[urllib.robotparser.RobotFileParser] = None
        self.robots_text = ""
        self.urls: Set[str] = set()
        self.downloads: Set[str] = set()
        self.external: Set[str] = set()
        self.skipped: List[Dict[str, object]] = []
        self.failures: List[Dict[str, object]] = []
        self.fetched: List[Dict[str, object]] = []

    def wait(self) -> None:
        elapsed = time.monotonic() - self.last_request_at
        if elapsed < self.config.request_delay_seconds:
            time.sleep(self.config.request_delay_seconds - elapsed)

    def allowed_by_policy(self, url: str, source: str) -> bool:
        if is_private_path(url, self.config.private_path_patterns):
            self.skipped.append({"url": url, "source": source, "reason": "private_or_form_like_path", "timestamp_utc": utc_now()})
            return False
        if self.robot_parser and self.config.respect_robots and not self.robot_parser.can_fetch(self.config.user_agent, url):
            self.skipped.append({"url": url, "source": source, "reason": "robots_disallow", "timestamp_utc": utc_now()})
            return False
        return True

    def fetch(self, url: str, source: str) -> Optional[requests.Response]:
        normalized = normalize_url(url, self.config.target_url)
        if not normalized:
            self.skipped.append({"url": url, "source": source, "reason": "unsupported_url", "timestamp_utc": utc_now()})
            return None
        if not same_domain(normalized, self.config.allowed_domains) and not is_download_url(normalized):
            self.external.add(normalized)
            return None
        if not self.allowed_by_policy(normalized, source):
            return None
        if self.config.dry_run:
            log_event(self.run_dir, "inventory", "dry_run_fetch", url=normalized, source=source)
            return None
        self.wait()
        try:
            response = self.session.get(normalized, timeout=self.config.request_timeout_seconds, allow_redirects=True)
            self.last_request_at = time.monotonic()
            self.fetched.append(
                {
                    "url": normalized,
                    "final_url": response.url,
                    "status": response.status_code,
                    "content_type": response.headers.get("Content-Type", ""),
                    "source": source,
                    "timestamp_local": local_now(),
                    "timestamp_utc": utc_now(),
                }
            )
            log_event(self.run_dir, "inventory", "fetched", url=normalized, status=response.status_code, source=source)
            return response
        except Exception as exc:
            self.failures.append({"url": normalized, "source": source, "error": str(exc), "timestamp_utc": utc_now()})
            log_event(self.run_dir, "inventory", "fetch_failed", url=normalized, source=source, error=str(exc))
            return None

    def capture_robots(self) -> None:
        response = self.fetch(urljoin(self.config.target_url, "/robots.txt"), "robots")
        if response and response.status_code < 400:
            self.robots_text = response.text
            raw = self.run_dir / "artifacts" / "control" / "robots.txt"
            raw.parent.mkdir(parents=True, exist_ok=True)
            raw.write_text(self.robots_text, encoding=response.encoding or "utf-8", errors="replace")
            self.robot_parser = build_robot_parser(self.config.target_url, self.robots_text)

    def sitemap_candidates(self) -> List[str]:
        candidates = []
        for line in self.robots_text.splitlines():
            if line.lower().startswith("sitemap:"):
                candidates.append(line.split(":", 1)[1].strip())
        candidates.append(urljoin(self.config.target_url, "/sitemap.xml"))
        return list(dict.fromkeys(candidates))

    def parse_sitemap(self, url: str, seen: Set[str], depth: int = 0) -> None:
        if depth > 5 or url in seen:
            return
        seen.add(url)
        response = self.fetch(url, "sitemap")
        if not response or response.status_code >= 400:
            return
        path = self.run_dir / "artifacts" / "control" / f"sitemap-{len(seen):03d}.xml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(response.content)
        try:
            root = ET.fromstring(response.content)
        except ET.ParseError as exc:
            self.failures.append({"url": url, "source": "sitemap", "error": f"parse_error: {exc}", "timestamp_utc": utc_now()})
            return
        for elem in root.iter():
            if elem.tag.rsplit("}", 1)[-1].lower() != "loc" or not elem.text:
                continue
            loc = normalize_url(elem.text.strip(), self.config.target_url)
            if not loc:
                continue
            if root.tag.rsplit("}", 1)[-1].lower() == "sitemapindex":
                self.parse_sitemap(loc, seen, depth + 1)
            elif same_domain(loc, self.config.allowed_domains):
                if self.allowed_by_policy(loc, "sitemap"):
                    self.urls.add(loc)

    def discover_links(self) -> None:
        pages = list(dict.fromkeys([self.config.target_url] + sorted(self.urls)))[: self.config.max_pages or None]
        for page_url in pages:
            response = self.fetch(page_url, "link_discovery")
            if not response or response.status_code >= 400:
                continue
            if not looks_like_html(response.url, response.headers.get("Content-Type", "")):
                continue
            parser = LinkExtractor()
            parser.feed(response.text)
            for href in parser.links:
                link = normalize_url(href, response.url)
                if not link:
                    continue
                if same_domain(link, self.config.allowed_domains):
                    if self.allowed_by_policy(link, "link"):
                        if is_download_url(link):
                            self.downloads.add(link)
                        else:
                            self.urls.add(link)
                elif is_download_url(link):
                    self.downloads.add(link)
                else:
                    self.external.add(link)

    def run(self) -> Dict[str, object]:
        log_event(self.run_dir, "inventory", "start", target_url=self.config.target_url)
        self.urls.add(normalize_url(self.config.target_url, self.config.target_url) or self.config.target_url)
        self.capture_robots()
        seen_sitemaps: Set[str] = set()
        for candidate in self.sitemap_candidates():
            self.parse_sitemap(candidate, seen_sitemaps)
        self.discover_links()
        result = {
            "target_url": self.config.target_url,
            "allowed_domains": self.config.allowed_domains,
            "urls": sorted(self.urls)[: self.config.max_pages or None],
            "download_urls": sorted(self.downloads),
            "external_urls_observed": sorted(self.external),
            "fetched": self.fetched,
            "skipped": self.skipped,
            "failures": self.failures,
            "access_policy": {"public_only": True, "forms_submitted": False, "accounts_created": False, "authentication_attempted": False},
            "completed_local": local_now(),
            "completed_utc": utc_now(),
        }
        write_json(self.run_dir / "manifest" / "url-inventory.json", result)
        log_event(self.run_dir, "inventory", "complete", urls=len(result["urls"]), skipped=len(self.skipped), failures=len(self.failures))
        return result


def run_inventory(config: CaptureConfig, run_dir: Path) -> Dict[str, object]:
    return InventoryRunner(config, run_dir).run()

