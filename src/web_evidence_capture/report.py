from pathlib import Path
from typing import Dict, List

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .config import CaptureConfig
from .logging_utils import local_now, read_json, utc_now, write_json
from .manifest import summarize_run


def template_environment() -> Environment:
    template_root = Path(__file__).resolve().parents[2] / "templates" / "reports"
    return Environment(loader=FileSystemLoader(str(template_root)), autoescape=select_autoescape(enabled_extensions=()))


def anomaly_lines(validation: Dict[str, object]) -> List[str]:
    lines = []
    for retry in validation.get("render_retries", []):
        lines.append(f"- Render retry for `{retry.get('url')}`; resolved: `{retry.get('resolved')}`.")
    for warning in validation.get("warnings", []):
        lines.append(f"- Warning: `{warning}`.")
    if not lines:
        lines.append("- No anomalies or retries recorded.")
    return lines


def generate_report(config: CaptureConfig, run_dir: Path) -> Dict[str, object]:
    summary = summarize_run(run_dir)
    inventory = read_json(run_dir / "manifest" / "url-inventory.json", {}) or {}
    capture = read_json(run_dir / "manifest" / "capture-result.json", {}) or {}
    render = read_json(run_dir / "manifest" / "render-result.json", []) or []
    privacy = read_json(run_dir / "manifest" / "privacy-result.json", {}) or {}
    wacz = read_json(run_dir / "manifest" / "wacz-result.json", {}) or {}
    validation = read_json(run_dir / "manifest" / "validation.json", {}) or {}
    env = template_environment()
    context = {
        "config": config.to_dict(),
        "summary": summary,
        "inventory": inventory,
        "capture": capture,
        "render": render,
        "privacy": privacy,
        "wacz": wacz,
        "validation": validation,
        "anomaly_lines": anomaly_lines(validation),
        "generated_local": local_now(),
        "generated_utc": utc_now(),
    }
    report_root = run_dir / "report"
    report_root.mkdir(parents=True, exist_ok=True)
    rendered_files = {}
    for name, output in [
        ("executive-summary.md.j2", "executive-summary.md"),
        ("methodology.md.j2", "methodology.md"),
        ("capture-report.md.j2", "capture-report.md"),
        ("integrity.md.j2", "integrity.md"),
        ("privacy-summary.md.j2", "privacy-summary.md"),
        ("limitations.md.j2", "limitations.md"),
        ("anomalies-retries.md.j2", "anomalies-retries.md"),
    ]:
        text = env.get_template(name).render(**context)
        path = report_root / output
        path.write_text(text, encoding="utf-8")
        rendered_files[output] = path.relative_to(run_dir).as_posix()
    combined = "\n\n".join((report_root / output).read_text(encoding="utf-8") for output in rendered_files)
    (report_root / "report.md").write_text(combined, encoding="utf-8")
    result = {"report_files": rendered_files, "combined_report": "report/report.md", "generated_local": local_now(), "generated_utc": utc_now()}
    write_json(run_dir / "manifest" / "report-result.json", result)
    return result

