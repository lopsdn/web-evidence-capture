import re
from pathlib import Path
from typing import Dict, Iterable, List


SECRET_PATTERNS = {
    "github_token": re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
    "aws_access_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "bearer_token": re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{20,}\b", re.I),
    "cookie_header": re.compile(r"\bCookie\s*:\s*[^\\n]{8,}", re.I),
    "private_key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "generic_secret_assignment": re.compile(
        r"\b(?:secret|token|api[_-]?key|password)\b\s*[:=]\s*[\"'][^\"']{8,}[\"']",
        re.I,
    ),
}

TEXT_SUFFIXES = {".py", ".md", ".txt", ".json", ".jsonl", ".yml", ".yaml", ".toml", ".j2", ".sh", ""}


def scan_text(text: str) -> List[Dict[str, str]]:
    findings: List[Dict[str, str]] = []
    for name, pattern in SECRET_PATTERNS.items():
        for match in pattern.finditer(text):
            findings.append({"type": name, "sample": mask_sample(match.group(0))})
    return findings


def mask_sample(value: str) -> str:
    if len(value) <= 12:
        return "***"
    return f"{value[:4]}...{value[-4:]}"


def scan_files(paths: Iterable[Path]) -> List[Dict[str, str]]:
    findings: List[Dict[str, str]] = []
    for path in paths:
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for finding in scan_text(text):
            finding["path"] = str(path)
            findings.append(finding)
    return findings


def scan_tree(root: Path) -> List[Dict[str, str]]:
    return scan_files(path for path in root.rglob("*") if ".git" not in path.parts)

