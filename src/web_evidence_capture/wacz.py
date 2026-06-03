import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlsplit, urlunsplit

from .config import CaptureConfig
from .logging_utils import local_now, log_event, read_json, utc_now, write_json


PAGES_DETECTED_RE = re.compile(r"Num Pages Detected:\s*(\d+)", re.I)
INVALID_PASSED_PAGE_RE = re.compile(r"Invalid passed page", re.I)


def parse_pages_detected(log_text: str) -> Optional[int]:
    match = PAGES_DETECTED_RE.search(log_text)
    return int(match.group(1)) if match else None


def normalize_page_url(url: str) -> str:
    parts = list(urlsplit(url.strip()))
    if not parts[2]:
        parts[2] = "/"
    parts[4] = ""
    return urlunsplit(parts)


def render_title_lookup(run_dir: Path) -> Dict[str, str]:
    render = read_json(run_dir / "manifest" / "render-result.json", []) or []
    titles: Dict[str, str] = {}
    for item in render:
        for key in ("final_url", "url"):
            url = item.get(key)
            title = item.get("title")
            if url and title:
                titles[normalize_page_url(str(url))] = str(title)
    return titles


def build_pages_jsonl(config: CaptureConfig, run_dir: Path) -> Dict[str, object]:
    capture = read_json(run_dir / "manifest" / "capture-result.json", {}) or {}
    pages_root = run_dir / "artifacts" / "wacz"
    pages_root.mkdir(parents=True, exist_ok=True)
    pages_path = pages_root / "pages.jsonl"
    render_titles = render_title_lookup(run_dir)
    seen = set()
    pages: List[Dict[str, object]] = []
    target = normalize_page_url(config.target_url)
    for index, item in enumerate(capture.get("captured_pages", []), start=1):
        url = normalize_page_url(str(item.get("final_url") or item.get("url") or ""))
        if not url or url in seen:
            continue
        seen.add(url)
        title = render_titles.get(url) or item.get("title") or url
        page = {
            "id": f"page-{len(pages) + 1:04d}",
            "url": url,
            "title": str(title),
        }
        if url.rstrip("/") == target.rstrip("/"):
            page["seed"] = True
        pages.append(page)
    header = {"format": "json-pages-1.0", "id": "pages", "title": f"{config.case_slug} captured pages"}
    with pages_path.open("w", encoding="utf-8") as handle:
        handle.write(json.dumps(header, sort_keys=True) + "\n")
        for page in pages:
            handle.write(json.dumps(page, sort_keys=True) + "\n")
    result = {"path": pages_path.relative_to(run_dir).as_posix(), "count": len(pages)}
    write_json(run_dir / "manifest" / "wacz-pages.json", result)
    return result


def count_wacz_pages(wacz_path: Path) -> Optional[int]:
    if not wacz_path.exists():
        return None
    try:
        with zipfile.ZipFile(wacz_path) as archive:
            with archive.open("pages/pages.jsonl") as handle:
                count = 0
                for index, raw_line in enumerate(handle):
                    if not raw_line.strip():
                        continue
                    if index == 0:
                        continue
                    count += 1
                return count
    except (KeyError, zipfile.BadZipFile, OSError):
        return None


def run_wacz(config: CaptureConfig, run_dir: Path) -> Dict[str, object]:
    capture = read_json(run_dir / "manifest" / "capture-result.json", {}) or {}
    warc_rel = capture.get("warc_path", "")
    warc_path = run_dir / warc_rel if warc_rel else None
    wacz_path = run_dir / "artifacts" / "wacz" / f"{config.case_slug}.wacz"
    wacz_path.parent.mkdir(parents=True, exist_ok=True)
    log_event(run_dir, "package_wacz", "start", warc_path=warc_rel)
    if config.dry_run or not warc_path or not warc_path.exists():
        result = {
            "warc_path": warc_rel,
            "wacz_path": "",
            "wacz_exists": False,
            "create_exit_code": None,
            "validate_exit_code": None,
            "pages_detected": None,
            "pages_input_path": "",
            "pages_input_count": 0,
            "warnings": ["warc_missing_or_dry_run"],
        }
        write_json(run_dir / "manifest" / "wacz-result.json", result)
        return result
    pages_input = build_pages_jsonl(config, run_dir)
    create_cmd = [
        sys.executable,
        "-m",
        "wacz",
        "create",
        "-o",
        str(wacz_path),
        "--hash-type",
        "sha256",
        "--title",
        f"{config.case_slug} public website evidence capture",
    ]
    if pages_input["count"]:
        create_cmd.extend(["--pages", str(run_dir / str(pages_input["path"]))])
    else:
        create_cmd.extend(["--url", config.target_url])
        create_cmd.append("-d")
    create_cmd.append(str(warc_path))
    create = subprocess.run(create_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=600)
    log_text = create.stdout
    validate = None
    if wacz_path.exists():
        validate_cmd = [sys.executable, "-m", "wacz", "validate", "-f", str(wacz_path)]
        validate = subprocess.run(validate_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=600)
        log_text += "\n" + validate.stdout
    log_path = run_dir / "logs" / "package_wacz.log"
    log_path.write_text(log_text, encoding="utf-8", errors="replace")
    pages_detected = parse_pages_detected(log_text)
    pages_detected_source = "wacz_log"
    if pages_detected is None:
        pages_detected = count_wacz_pages(wacz_path)
        pages_detected_source = "wacz_pages_jsonl"
    invalid_passed_pages_count = len(INVALID_PASSED_PAGE_RE.findall(log_text))
    warnings = []
    if pages_detected == 0:
        warnings.append("wacz_valid_but_zero_pages_detected")
    if invalid_passed_pages_count:
        warnings.append("wacz_pages_unmatched_to_warc")
    result = {
        "warc_path": warc_rel,
        "wacz_path": wacz_path.relative_to(run_dir).as_posix(),
        "wacz_exists": wacz_path.exists(),
        "create_exit_code": create.returncode,
        "validate_exit_code": validate.returncode if validate else None,
        "pages_detected": pages_detected,
        "pages_detected_source": pages_detected_source,
        "pages_input_path": pages_input["path"],
        "pages_input_count": pages_input["count"],
        "invalid_passed_pages_count": invalid_passed_pages_count,
        "zero_pages_policy": config.wacz_zero_pages_policy,
        "warnings": warnings,
        "log": log_path.relative_to(run_dir).as_posix(),
        "completed_local": local_now(),
        "completed_utc": utc_now(),
    }
    write_json(run_dir / "manifest" / "wacz-result.json", result)
    log_event(
        run_dir,
        "package_wacz",
        "complete",
        exists=wacz_path.exists(),
        pages_detected=pages_detected,
        pages_input_count=pages_input["count"],
        warnings=warnings,
    )
    return result
