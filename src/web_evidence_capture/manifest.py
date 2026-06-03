from pathlib import Path
from typing import Any, Dict, List

from .logging_utils import read_json, write_json


def load_manifest(run_dir: Path, name: str, default: Any = None) -> Any:
    return read_json(run_dir / "manifest" / name, default)


def write_manifest(run_dir: Path, name: str, value: Any) -> None:
    write_json(run_dir / "manifest" / name, value)


def summarize_run(run_dir: Path) -> Dict[str, Any]:
    inventory = load_manifest(run_dir, "url-inventory.json", {}) or {}
    capture = load_manifest(run_dir, "capture-result.json", {}) or {}
    render = load_manifest(run_dir, "render-result.json", []) or []
    wacz = load_manifest(run_dir, "wacz-result.json", {}) or {}
    validation = load_manifest(run_dir, "validation.json", {}) or {}
    summary = {
        "target_url": inventory.get("target_url") or capture.get("target_url"),
        "inventory_url_count": len(inventory.get("urls", [])),
        "captured_pages": len(capture.get("captured_pages", [])),
        "downloads": len(capture.get("downloads", [])),
        "skipped": len(inventory.get("skipped", [])) + len(capture.get("skipped", [])),
        "failures": len(inventory.get("failures", [])) + len(capture.get("failures", [])),
        "rendered_pages": len(render),
        "render_retries": count_retries(render),
        "warc_exists": bool(capture.get("warc_path")),
        "wacz_exists": bool(wacz.get("wacz_exists")),
        "wacz_pages_detected": wacz.get("pages_detected"),
        "validation_status": validation.get("status"),
    }
    write_manifest(run_dir, "evidence-summary.json", summary)
    return summary


def count_retries(render_results: List[Dict[str, Any]]) -> int:
    return sum(len(item.get("attempts", [])) - 1 for item in render_results if item.get("attempts"))

