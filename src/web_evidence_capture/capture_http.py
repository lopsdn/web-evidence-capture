import contextlib
import mimetypes
import re
import time
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Optional, Set

import requests

from .config import CaptureConfig
from .logging_utils import local_now, log_event, read_json, utc_now, write_json
from .mirror import (
    LinkExtractor,
    disable_executable_scripts,
    is_download_url,
    local_page_path,
    looks_like_html,
    normalize_url,
    relative_link,
    same_domain,
)


class WarcWriterAdapter:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        from warcio.statusandheaders import StatusAndHeaders
        from warcio.warcwriter import WARCWriter

        self.status_headers = StatusAndHeaders
        self.file_handle = path.open("wb")
        self.writer = WARCWriter(self.file_handle, gzip=True)

    def write_response(self, requested_url: str, response: requests.Response) -> None:
        status = f"{response.status_code} {response.reason or ''}".strip()
        headers = [(str(key), str(value)) for key, value in response.headers.items()]
        http_headers = self.status_headers(status, headers, protocol="HTTP/1.1")
        record = self.writer.create_warc_record(
            response.url or requested_url,
            "response",
            payload=BytesIO(response.content),
            http_headers=http_headers,
        )
        self.writer.write_record(record)

    def close(self) -> None:
        self.file_handle.close()


class HttpCaptureRunner:
    def __init__(self, config: CaptureConfig, run_dir: Path) -> None:
        self.config = config
        self.run_dir = run_dir
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": config.user_agent, "Accept": "*/*"})
        self.last_request_at = 0.0
        self.mirror_root = run_dir / "artifacts" / "mirror"
        self.download_root = run_dir / "artifacts" / "downloads"
        self.warc_path = run_dir / "artifacts" / "warc" / f"{config.case_slug}.warc.gz"
        self.warc: Optional[WarcWriterAdapter] = None
        self.captured_pages: List[Dict[str, object]] = []
        self.downloads: List[Dict[str, object]] = []
        self.fetched: List[Dict[str, object]] = []
        self.skipped: List[Dict[str, object]] = []
        self.failures: List[Dict[str, object]] = []
        self.forms_observed: List[Dict[str, object]] = []
        self.seen: Set[str] = set()

    def wait(self) -> None:
        elapsed = time.monotonic() - self.last_request_at
        if elapsed < self.config.request_delay_seconds:
            time.sleep(self.config.request_delay_seconds - elapsed)

    def fetch(self, url: str, source: str) -> Optional[requests.Response]:
        if self.config.dry_run:
            log_event(self.run_dir, "capture", "dry_run_fetch", url=url, source=source)
            return None
        self.wait()
        try:
            response = self.session.get(url, timeout=self.config.request_timeout_seconds, allow_redirects=True)
            self.last_request_at = time.monotonic()
            if self.warc:
                self.warc.write_response(url, response)
            self.fetched.append(
                {
                    "url": url,
                    "final_url": response.url,
                    "status": response.status_code,
                    "content_type": response.headers.get("Content-Type", ""),
                    "source": source,
                    "timestamp_local": local_now(),
                    "timestamp_utc": utc_now(),
                }
            )
            log_event(self.run_dir, "capture", "fetched", url=url, status=response.status_code, source=source)
            return response
        except Exception as exc:
            self.failures.append({"url": url, "source": source, "error": str(exc), "timestamp_utc": utc_now()})
            log_event(self.run_dir, "capture", "fetch_failed", url=url, error=str(exc), source=source)
            return None

    def save_page(self, url: str, response: requests.Response) -> None:
        parser = LinkExtractor()
        parser.feed(response.text)
        local_path = local_page_path(self.mirror_root, response.url)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        rewritten = self.rewrite_links(response.url, response.text)
        rewritten = disable_executable_scripts(rewritten)
        local_path.write_text(rewritten, encoding="utf-8", errors="replace")
        if normalize_url(response.url, self.config.target_url).rstrip("/") == normalize_url(self.config.target_url, self.config.target_url).rstrip("/"):
            index_path = self.mirror_root / "index.html"
            if local_path != index_path:
                index_path.write_text(rewritten, encoding="utf-8", errors="replace")
        self.captured_pages.append(
            {
                "url": url,
                "final_url": response.url,
                "status": response.status_code,
                "content_type": response.headers.get("Content-Type", ""),
                "title": parser.title,
                "visible_text_length": len(parser.body_text),
                "local_path": local_path.relative_to(self.run_dir).as_posix(),
                "timestamp_local": local_now(),
                "timestamp_utc": utc_now(),
            }
        )
        for action in parser.forms:
            self.forms_observed.append({"page_url": response.url, "action": action, "note": "Form observed but not submitted"})

    def rewrite_links(self, page_url: str, text: str) -> str:
        def replace(match: re.Match) -> str:
            quote = match.group(1)
            href = match.group(2)
            absolute = normalize_url(href, page_url)
            if not absolute or not same_domain(absolute, self.config.allowed_domains) or is_download_url(absolute):
                return match.group(0)
            target = local_page_path(self.mirror_root, absolute)
            current = local_page_path(self.mirror_root, page_url)
            return f'href={quote}{relative_link(current, target)}{quote}'

        return re.sub(r"href=(['\"])([^'\"]+)\1", replace, text, flags=re.I)

    def save_download(self, url: str, response: requests.Response) -> None:
        filename = Path(response.url.split("?", 1)[0]).name or "download"
        suffix = Path(filename).suffix
        if not suffix:
            suffix = mimetypes.guess_extension(response.headers.get("Content-Type", "").split(";", 1)[0]) or ""
            filename += suffix
        filename = re.sub(r"[^A-Za-z0-9._-]+", "_", filename)[:160]
        path = self.download_root / filename
        index = 2
        while path.exists():
            path = self.download_root / f"{Path(filename).stem}-{index}{Path(filename).suffix}"
            index += 1
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(response.content)
        self.downloads.append(
            {
                "url": url,
                "final_url": response.url,
                "status": response.status_code,
                "content_type": response.headers.get("Content-Type", ""),
                "local_path": path.relative_to(self.run_dir).as_posix(),
                "timestamp_utc": utc_now(),
            }
        )

    def run(self) -> Dict[str, object]:
        inventory = read_json(self.run_dir / "manifest" / "url-inventory.json", {}) or {}
        urls = inventory.get("urls", [])
        download_urls = inventory.get("download_urls", [])
        if not urls:
            urls = [self.config.target_url]
        log_event(self.run_dir, "capture", "start", urls=len(urls), downloads=len(download_urls))
        if not self.config.dry_run:
            self.warc = WarcWriterAdapter(self.warc_path)
        try:
            for url in urls[: self.config.max_pages or None]:
                normalized = normalize_url(url, self.config.target_url)
                if not normalized or normalized in self.seen:
                    continue
                self.seen.add(normalized)
                if not same_domain(normalized, self.config.allowed_domains):
                    self.skipped.append({"url": normalized, "reason": "outside_allowed_domains", "timestamp_utc": utc_now()})
                    continue
                response = self.fetch(normalized, "inventory")
                if not response or response.status_code >= 400:
                    continue
                if is_download_url(response.url, response.headers.get("Content-Type", "")):
                    self.save_download(normalized, response)
                elif looks_like_html(response.url, response.headers.get("Content-Type", "")):
                    self.save_page(normalized, response)
            for url in download_urls:
                normalized = normalize_url(url, self.config.target_url)
                if not normalized or normalized in self.seen:
                    continue
                self.seen.add(normalized)
                response = self.fetch(normalized, "download_inventory")
                if response and response.status_code < 400:
                    self.save_download(normalized, response)
        finally:
            if self.warc:
                with contextlib.suppress(Exception):
                    self.warc.close()
        result = {
            "target_url": self.config.target_url,
            "warc_path": self.warc_path.relative_to(self.run_dir).as_posix() if self.warc_path.exists() else "",
            "captured_pages": self.captured_pages,
            "downloads": self.downloads,
            "fetched": self.fetched,
            "skipped": self.skipped,
            "failures": self.failures,
            "forms_observed_not_submitted": self.forms_observed,
            "access_policy": {"public_only": True, "forms_submitted": False, "accounts_created": False, "authentication_attempted": False},
            "completed_local": local_now(),
            "completed_utc": utc_now(),
        }
        write_json(self.run_dir / "manifest" / "capture-result.json", result)
        log_event(self.run_dir, "capture", "complete", pages=len(self.captured_pages), downloads=len(self.downloads), failures=len(self.failures))
        return result


def run_capture(config: CaptureConfig, run_dir: Path) -> Dict[str, object]:
    return HttpCaptureRunner(config, run_dir).run()

