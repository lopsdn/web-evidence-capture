import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from .logging_utils import local_now, utc_now, write_json


PRIVATE_PATH_PATTERNS = [
    r"/wp-admin\b",
    r"/admin\b",
    r"/login\b",
    r"/log-in\b",
    r"/signin\b",
    r"/sign-in\b",
    r"/account\b",
    r"/dashboard\b",
    r"/portal\b",
    r"/auth\b",
    r"/apply\b",
    r"/schedule\b",
    r"/meeting\b",
]

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (compatible; web-evidence-capture/0.1; "
    "+https://github.com/lopsdn/web-evidence-capture)"
)


@dataclass
class CaptureConfig:
    target_url: str
    case_slug: str
    allowed_domains: List[str]
    max_pages: int = 25
    cookie_choice: str = "none"
    request_delay_seconds: float = 1.0
    request_timeout_seconds: int = 30
    output_root: str = "cases"
    dry_run: bool = False
    user_agent: str = DEFAULT_USER_AGENT
    respect_robots: bool = True
    max_asset_bytes: int = 25 * 1024 * 1024
    min_mirror_body_chars: int = 80
    wacz_zero_pages_policy: str = "warning"
    render_retries: int = 1
    private_path_patterns: List[str] = field(default_factory=lambda: list(PRIVATE_PATH_PATTERNS))

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def normalize_allowed_domains(target_url: str, allowed_domains: Optional[List[str]]) -> List[str]:
    if allowed_domains:
        return sorted({domain.strip().lower() for domain in allowed_domains if domain.strip()})
    parsed = urlparse(target_url)
    if not parsed.netloc:
        raise ValueError("target_url must include a host")
    host = parsed.netloc.lower()
    domains = {host}
    if host.startswith("www."):
        domains.add(host[4:])
    else:
        domains.add(f"www.{host}")
    return sorted(domains)


def slugify(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip().lower()).strip("-")
    if not slug:
        raise ValueError("case_slug cannot be empty")
    return slug[:120]


def load_config(path: Path) -> CaptureConfig:
    data = json.loads(path.read_text(encoding="utf-8"))
    return config_from_dict(data)


def config_from_dict(data: Dict[str, Any]) -> CaptureConfig:
    target_url = data["target_url"].strip()
    if urlparse(target_url).scheme not in {"http", "https"}:
        raise ValueError("target_url must be http or https")
    case_slug = slugify(data["case_slug"])
    allowed_domains = normalize_allowed_domains(target_url, data.get("allowed_domains"))
    values = dict(data)
    values["target_url"] = target_url
    values["case_slug"] = case_slug
    values["allowed_domains"] = allowed_domains
    return CaptureConfig(**values)


def run_timestamp(now: Optional[datetime] = None) -> str:
    value = now or datetime.now().astimezone()
    return value.strftime("%Y-%m-%d-%H%M")


def case_dir(config: CaptureConfig, root: Optional[Path] = None) -> Path:
    base = root if root is not None else Path(config.output_root)
    return base / config.case_slug


def run_dir(config: CaptureConfig, timestamp: Optional[str] = None, root: Optional[Path] = None) -> Path:
    return case_dir(config, root=root) / "runs" / (timestamp or run_timestamp())


def ensure_run_dirs(path: Path) -> None:
    for name in ["report", "manifest", "validation", "logs", "hashes", "artifacts"]:
        (path / name).mkdir(parents=True, exist_ok=True)


def init_case(config: CaptureConfig, timestamp: Optional[str] = None, root: Optional[Path] = None) -> Path:
    path = run_dir(config, timestamp=timestamp, root=root)
    ensure_run_dirs(path)
    metadata = {
        "case_slug": config.case_slug,
        "target_url": config.target_url,
        "allowed_domains": config.allowed_domains,
        "created_local": local_now(),
        "created_utc": utc_now(),
        "status": "initialized",
        "access_policy": {
            "public_only": True,
            "authentication_attempted": False,
            "accounts_created": False,
            "forms_submitted": False,
            "target_contacted_outside_public_gets": False,
        },
        "config": config.to_dict(),
    }
    write_json(path / "manifest" / "package-metadata.json", metadata)
    return path

