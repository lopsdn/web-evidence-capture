import hashlib
from pathlib import Path
from typing import Dict, List, Set

from .logging_utils import write_json


HASH_EXCLUDED_RELATIVE_PATHS = {
    "hashes/files.sha256",
    "manifest/file-manifest.json",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def hash_files(root: Path, excluded_relative_paths: Set[str] = None) -> List[Dict[str, object]]:
    excluded = excluded_relative_paths or HASH_EXCLUDED_RELATIVE_PATHS
    rows: List[Dict[str, object]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if rel in excluded:
            continue
        rows.append({"path": rel, "size_bytes": path.stat().st_size, "sha256": sha256_file(path)})
    return rows


def write_hashes(root: Path) -> List[Dict[str, object]]:
    rows = hash_files(root)
    write_json(root / "manifest" / "file-manifest.json", rows)
    (root / "hashes").mkdir(parents=True, exist_ok=True)
    with (root / "hashes" / "files.sha256").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(f"{row['sha256']}  {row['path']}\n")
    return rows

