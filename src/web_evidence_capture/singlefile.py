import shutil
import subprocess
from pathlib import Path
from typing import Dict, List

from .config import CaptureConfig
from .logging_utils import local_now, log_event, utc_now, write_json
from .render import selected_urls


def run_singlefile(config: CaptureConfig, run_dir: Path) -> List[Dict[str, object]]:
    urls = selected_urls(run_dir, config)
    output_root = run_dir / "artifacts" / "singlefile"
    output_root.mkdir(parents=True, exist_ok=True)
    binary = shutil.which("single-file")
    results: List[Dict[str, object]] = []
    log_event(run_dir, "singlefile", "start", urls=len(urls), available=bool(binary))
    if config.dry_run or not binary:
        for url in urls:
            results.append({"url": url, "output": "", "exists": False, "exit_code": None, "skipped_reason": "dry_run" if config.dry_run else "single_file_cli_not_found"})
        write_json(run_dir / "manifest" / "singlefile-result.json", results)
        return results
    for index, url in enumerate(urls, start=1):
        output = output_root / f"{index:03d}.singlefile.html"
        command = [
            binary,
            url,
            str(output),
            "--browser-width",
            "1440",
            "--browser-height",
            "1000",
            "--browser-wait-until",
            "networkIdle",
            "--browser-load-max-time",
            "90000",
            "--browser-capture-max-time",
            "90000",
            "--max-parallel-workers",
            "1",
            "--filename-conflict-action",
            "overwrite",
        ]
        log_event(run_dir, "singlefile", "export", url=url, index=index)
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=180)
        log_path = run_dir / "logs" / f"singlefile-{index:03d}.log"
        log_path.write_text(result.stdout, encoding="utf-8", errors="replace")
        results.append(
            {
                "url": url,
                "output": output.relative_to(run_dir).as_posix(),
                "exists": output.exists(),
                "exit_code": result.returncode,
                "log": log_path.relative_to(run_dir).as_posix(),
                "timestamp_local": local_now(),
                "timestamp_utc": utc_now(),
            }
        )
    write_json(run_dir / "manifest" / "singlefile-result.json", results)
    log_event(run_dir, "singlefile", "complete", outputs=sum(1 for item in results if item.get("exists")))
    return results

