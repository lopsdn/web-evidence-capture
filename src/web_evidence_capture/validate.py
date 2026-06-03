from pathlib import Path
from typing import Dict, List

from .config import CaptureConfig
from .hashing import write_hashes
from .logging_utils import local_now, log_event, read_json, utc_now, write_json
from .mirror import extract_visible_text_from_html
from .sensitive_scan import scan_tree


def collect_render_retries(render_results: List[Dict[str, object]]) -> List[Dict[str, object]]:
    retries = []
    for item in render_results:
        attempts = item.get("attempts", [])
        if len(attempts) > 1:
            retries.append({"url": item.get("url"), "attempts": attempts, "resolved": not item.get("error")})
    return retries


def validate_run(config: CaptureConfig, run_dir: Path, write_hash_manifest: bool = True) -> Dict[str, object]:
    capture = read_json(run_dir / "manifest" / "capture-result.json", {}) or {}
    render = read_json(run_dir / "manifest" / "render-result.json", []) or []
    wacz = read_json(run_dir / "manifest" / "wacz-result.json", {}) or {}
    metadata = read_json(run_dir / "manifest" / "package-metadata.json", {}) or {}
    mirror_index = run_dir / "artifacts" / "mirror" / "index.html"
    mirror_text = ""
    if mirror_index.exists():
        mirror_text = extract_visible_text_from_html(mirror_index.read_text(encoding="utf-8", errors="ignore"))
    screenshots = list((run_dir / "artifacts" / "screenshots").glob("*.png"))
    pdfs = list((run_dir / "artifacts" / "pdf").glob("*.pdf"))
    missing_render_artifacts = []
    for item in render:
        screenshot = item.get("screenshot")
        pdf = item.get("pdf")
        if screenshot and not (run_dir / screenshot).exists():
            missing_render_artifacts.append({"url": item.get("url"), "path": screenshot})
        if pdf and not (run_dir / pdf).exists():
            missing_render_artifacts.append({"url": item.get("url"), "path": pdf})
    warc_path = run_dir / capture.get("warc_path", "")
    wacz_path = run_dir / wacz.get("wacz_path", "")
    retries = collect_render_retries(render)
    sensitive_findings = scan_tree(run_dir)
    checks = {
        "mirror_index_exists": mirror_index.exists(),
        "mirror_meaningful_body_exists": len(mirror_text.strip()) >= config.min_mirror_body_chars,
        "mirror_body_sample": mirror_text[:300],
        "warc_exists": warc_path.exists() if capture.get("warc_path") else False,
        "wacz_exists": wacz_path.exists() if wacz.get("wacz_path") else False,
        "wacz_validate_exit_code": wacz.get("validate_exit_code"),
        "wacz_pages_detected": wacz.get("pages_detected"),
        "screenshots_count": len(screenshots),
        "pdf_count": len(pdfs),
        "render_result_count": len(render),
        "render_failures_count": sum(1 for item in render if item.get("error")),
        "missing_render_artifacts_count": len(missing_render_artifacts),
        "retry_count": len(retries),
        "forms_submitted": False,
        "accounts_created": False,
        "authentication_attempted": False,
        "sensitive_findings_count": len(sensitive_findings),
    }
    warnings = []
    failures = []
    if not checks["mirror_index_exists"]:
        failures.append("mirror_index_missing")
    if not checks["mirror_meaningful_body_exists"]:
        failures.append("mirror_body_empty_or_too_short")
    if not checks["warc_exists"]:
        failures.append("warc_missing")
    if not checks["wacz_exists"]:
        failures.append("wacz_missing")
    if checks["wacz_validate_exit_code"] not in (0, None):
        failures.append("wacz_validation_failed")
    if checks["wacz_pages_detected"] == 0:
        if config.wacz_zero_pages_policy == "fail":
            failures.append("wacz_zero_pages_detected")
        else:
            warnings.append("wacz_zero_pages_detected")
    if checks["render_failures_count"]:
        failures.append("render_failures_present")
    if missing_render_artifacts:
        failures.append("render_artifacts_missing")
    if sensitive_findings:
        failures.append("sensitive_patterns_detected")
    if retries:
        warnings.append("render_retries_recorded")
    status = "failed_validation" if failures else "completed_with_warnings" if warnings else "completed_validated"
    result = {
        "status": status,
        "checks": checks,
        "warnings": warnings,
        "failures": failures,
        "render_retries": retries,
        "missing_render_artifacts": missing_render_artifacts,
        "sensitive_findings": sensitive_findings,
        "completed_local": local_now(),
        "completed_utc": utc_now(),
    }
    write_json(run_dir / "validation" / "validation.json", result)
    write_json(run_dir / "manifest" / "validation.json", result)
    if write_hash_manifest:
        rows = write_hashes(run_dir)
        result["checks"]["hashed_file_count"] = len(rows)
        write_json(run_dir / "validation" / "validation.json", result)
        write_json(run_dir / "manifest" / "validation.json", result)
    metadata["status"] = status
    metadata["completed_local"] = local_now()
    metadata["completed_utc"] = utc_now()
    write_json(run_dir / "manifest" / "package-metadata.json", metadata)
    log_event(run_dir, "validate", "complete", status=status, failures=failures, warnings=warnings)
    return result
