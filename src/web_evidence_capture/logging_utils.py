import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def local_now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def log_event(run_dir: Path, step: str, message: str, **fields: Any) -> None:
    logs_dir = run_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    record: Dict[str, Any] = {
        "timestamp_local": local_now(),
        "timestamp_utc": utc_now(),
        "step": step,
        "message": message,
    }
    record.update(fields)
    line = json.dumps(record, sort_keys=True, ensure_ascii=False)
    print(line, flush=True)
    with (logs_dir / f"{step}.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))

