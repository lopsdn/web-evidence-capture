import hashlib
import html
import os
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import unquote, urljoin, urlparse, urlunparse


DOWNLOAD_EXTENSIONS = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".zip", ".csv", ".txt", ".rtf"}
STATIC_EXTENSIONS = {
    ".css",
    ".js",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".webp",
    ".avif",
    ".ico",
    ".woff",
    ".woff2",
    ".ttf",
    ".otf",
    ".eot",
    ".mp4",
    ".webm",
}
SKIP_SCHEMES = {"mailto", "tel", "javascript", "data", "sms"}


class LinkExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: List[str] = []
        self.resources: List[Tuple[str, str]] = []
        self.forms: List[str] = []
        self.title_parts: List[str] = []
        self.body_parts: List[str] = []
        self._in_title = False
        self._skip_text = False

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        attr = {key.lower(): value for key, value in attrs if value}
        lowered = tag.lower()
        if lowered == "title":
            self._in_title = True
        if lowered in {"script", "style", "noscript"}:
            self._skip_text = True
        if lowered == "a" and attr.get("href"):
            self.links.append(attr["href"])
        if lowered == "form":
            self.forms.append(attr.get("action", ""))
        if lowered == "link" and attr.get("href"):
            rel = set((attr.get("rel") or "").lower().split())
            if rel.intersection({"stylesheet", "icon", "shortcut", "apple-touch-icon", "preload", "modulepreload"}):
                self.resources.append(("href", attr["href"]))
        if lowered in {"script", "img", "source", "video", "audio", "iframe"}:
            for key in ("src", "poster"):
                if attr.get(key):
                    self.resources.append((key, attr[key]))

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if lowered == "title":
            self._in_title = False
        if lowered in {"script", "style", "noscript"}:
            self._skip_text = False

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if not text:
            return
        if self._in_title:
            self.title_parts.append(text)
        elif not self._skip_text:
            self.body_parts.append(text)

    @property
    def title(self) -> str:
        return " ".join(self.title_parts).strip()

    @property
    def body_text(self) -> str:
        return " ".join(self.body_parts).strip()


def normalize_url(url: str, base: str = "") -> Optional[str]:
    if not url:
        return None
    value = html.unescape(url).strip()
    parsed = urlparse(value)
    if parsed.scheme and parsed.scheme.lower() in SKIP_SCHEMES:
        return None
    if not parsed.scheme and base:
        value = urljoin(base, value)
        parsed = urlparse(value)
    if parsed.scheme.lower() not in {"http", "https"}:
        return None
    path = parsed.path or "/"
    return urlunparse(parsed._replace(fragment="", path=path))


def same_domain(url: str, allowed_domains: List[str]) -> bool:
    return urlparse(url).netloc.lower() in {domain.lower() for domain in allowed_domains}


def is_private_path(url: str, patterns: List[str]) -> bool:
    path = urlparse(url).path
    return any(re.search(pattern, path, re.I) for pattern in patterns)


def is_download_url(url: str, content_type: str = "") -> bool:
    suffix = Path(urlparse(url).path).suffix.lower()
    if suffix in DOWNLOAD_EXTENSIONS:
        return True
    lowered = content_type.lower()
    return any(marker in lowered for marker in ["application/pdf", "application/zip", "text/csv", "application/msword"])


def looks_like_html(url: str, content_type: str) -> bool:
    suffix = Path(urlparse(url).path).suffix.lower()
    if suffix in DOWNLOAD_EXTENSIONS or suffix in STATIC_EXTENSIONS:
        return False
    lowered = content_type.lower()
    return not lowered or "text/html" in lowered or "application/xhtml" in lowered


def local_page_path(mirror_root: Path, url: str) -> Path:
    parsed = urlparse(url)
    path = unquote(parsed.path or "/")
    if path.endswith("/"):
        path += "index.html"
    elif not Path(path).suffix:
        path += "/index.html"
    elif Path(path).suffix.lower() not in {".html", ".htm"}:
        path += ".html"
    if parsed.query:
        digest = hashlib.sha256(parsed.query.encode("utf-8")).hexdigest()[:10]
        stem = Path(path).stem
        suffix = Path(path).suffix
        path = str(Path(path).with_name(f"{stem}-{digest}{suffix}"))
    return mirror_root / path.lstrip("/")


def relative_link(from_path: Path, to_path: Path) -> str:
    return os.path.relpath(to_path, from_path.parent)


def disable_executable_scripts(text: str) -> str:
    note = (
        "<!-- Offline mirror note: executable scripts are disabled in mirror HTML only. "
        "Raw HTTP responses are preserved in WARC when WARC capture is available. -->"
    )
    text = re.sub(r"</head>", note + "\n</head>", text, count=1, flags=re.I) if re.search(r"</head>", text, re.I) else note + "\n" + text

    def replace(match: re.Match) -> str:
        attrs = match.group(1) or ""
        type_match = re.search(r"\s+type\s*=\s*(['\"])(.*?)\1", attrs, re.I)
        script_type = (type_match.group(2) if type_match else "").lower()
        if "json" in script_type and "javascript" not in script_type:
            return match.group(0)
        if type_match:
            attrs = re.sub(r"\s+type\s*=\s*(['\"])(.*?)\1", ' type="application/x-offline-preserved-script"', attrs, count=1, flags=re.I)
            return f"<script{attrs}>"
        return f'<script type="application/x-offline-preserved-script"{attrs}>'

    return re.sub(r"<script\b([^>]*)>", replace, text, flags=re.I)


def extract_visible_text_from_html(text: str) -> str:
    parser = LinkExtractor()
    parser.feed(text)
    return parser.body_text

