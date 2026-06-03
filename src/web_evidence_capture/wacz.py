import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, Optional

from .config import CaptureConfig
from .logging_utils import local_now, log_event, read_json, utc_now, write_json


PAGES_DETECTED_RE = re.compile(r"Num Pages Detected:\s*(\d+)", re.I)


def parse_pages_detected(log_text: str) -> Optional[int]:
    match = PAGES_DETECTED_RE.search(log_text)
    return int(match.group(1)) if match else None


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
            "warnings": ["warc_missing_or_dry_run"],
        }
        write_json(run_dir / "manifest" / "wacz-result.json", result)
        return result
    create_cmd = [
        sys.executable,
        "-m",
        "wacz",
        "create",
        "-o",
        str(wacz_path),
        "-d",
        "--hash-type",
        "sha256",
        "--title",
        f"{config.case_slug} public website evidence capture",
        "--url",
        config.target_url,
        str(warc_path),
    ]
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
    warnings = []
    if pages_detected == 0:
        warnings.append("wacz_valid_but_zero_pages_detected")
    result = {
        "warc_path": warc_rel,
        "wacz_path": wacz_path.relative_to(run_dir).as_posix(),
        "wacz_exists": wacz_path.exists(),
        "create_exit_code": create.returncode,
        "validate_exit_code": validate.returncode if validate else None,
        "pages_detected": pages_detected,
        "zero_pages_policy": config.wacz_zero_pages_policy,
        "warnings": warnings,
        "log": log_path.relative_to(run_dir).as_posix(),
        "completed_local": local_now(),
        "completed_utc": utc_now(),
    }
    write_json(run_dir / "manifest" / "wacz-result.json", result)
    log_event(run_dir, "package_wacz", "complete", exists=wacz_path.exists(), pages_detected=pages_detected, warnings=warnings)
    return result

