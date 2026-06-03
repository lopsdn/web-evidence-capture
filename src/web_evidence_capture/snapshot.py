import hashlib
import html
import json
import re
import shutil
import zipfile
from pathlib import Path
from typing import Dict, List, Tuple
from urllib.parse import urljoin, urlparse

from .config import CaptureConfig
from .hashing import sha256_file, write_hashes
from .logging_utils import utc_now, write_json
from .mirror import is_download_url, local_page_path, normalize_url, relative_link, same_domain


STAGE_ORDER = [
    "scope",
    "inventory",
    "capture",
    "render",
    "privacy_inspection",
    "singlefile",
    "package_wacz",
    "hash_manifest",
    "validate",
    "generate_report",
    "final",
]

GITHUB_GIT_FILE_LIMIT_BYTES = 100 * 1024 * 1024
DEFAULT_ARCHIVE_COMMIT_LIMIT_BYTES = 95 * 1024 * 1024


def site_slug(target_url: str, fallback: str) -> str:
    host = urlparse(target_url).netloc.lower() or fallback
    return re.sub(r"[^a-z0-9.-]+", "-", host).strip("-") or fallback


def add_tree(archive: zipfile.ZipFile, source: Path, prefix: str) -> int:
    if not source.exists():
        return 0
    count = 0
    for file_path in sorted(source.rglob("*")):
        if file_path.is_file():
            archive.write(file_path, f"{prefix}/{file_path.relative_to(source).as_posix()}")
            count += 1
    return count


def read_json_file(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def local_url_for_page(mirror_root: Path, page_path: Path, target_url: str) -> str:
    relative = page_path.relative_to(mirror_root)
    if relative.name == "index.html":
        parent = relative.parent.as_posix()
        path = "/" if parent == "." else f"/{parent}/"
    else:
        path = f"/{relative.as_posix()}"
    return urljoin(target_url, path)


def not_captured_page(url: str, sitemap_link: str) -> str:
    return "\n".join(
        [
            "<!doctype html>",
            '<meta charset="utf-8">',
            "<title>Page Not Captured</title>",
            '<style>body{font-family:system-ui,sans-serif;max-width:760px;margin:48px auto;padding:0 24px;line-height:1.55;color:#1f2937}code{word-break:break-all;background:#f3f4f6;padding:2px 4px;border-radius:4px}a{color:#1d4ed8}</style>',
            "<h1>Page Not Captured</h1>",
            "<p>This link points to a same-domain URL that was not present in the captured mirror for this run.</p>",
            f"<p>Original URL: <code>{html.escape(url)}</code></p>",
            "<p>The page may have been outside the discovered inventory, skipped by capture policy, generated only by client-side code, or unavailable during capture.</p>",
            f'<p><a href="{html.escape(sitemap_link)}">Return to the offline site map</a></p>',
            "",
        ]
    )


def not_captured_page_path(mirror_root: Path, url: str) -> Path:
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
    return mirror_root / "_not-captured" / f"{digest}.html"


def offline_navigation_helper(site_map_href: str) -> str:
    site_map_json = json.dumps(site_map_href)
    return "\n".join(
        [
            '<script data-web-evidence-offline-helper="1">',
            "(function(){",
            f"var siteMapHref={site_map_json};",
            "function hasModifier(event){return event.metaKey||event.ctrlKey||event.shiftKey||event.altKey;}",
            "function navigateToLink(link,event){",
            "  var href=(link.getAttribute('href')||'').trim();",
            "  if(!href||href==='#'){return false;}",
            "  if(event){event.preventDefault();event.stopPropagation();}",
            "  window.location.href=link.href;",
            "  return true;",
            "}",
            "function normalizedText(node){return (node&&node.textContent||'').replace(/\\s+/g,' ').trim().toLowerCase();}",
            "function findLinkByLabel(label){",
            "  if(!label){return null;}",
            "  var links=Array.prototype.slice.call(document.querySelectorAll('a[href]'));",
            "  var exact=links.find(function(link){",
            "    var href=(link.getAttribute('href')||'').trim();",
            "    return href&&href!=='#'&&normalizedText(link)===label;",
            "  });",
            "  if(exact){return exact;}",
            "  return links.find(function(link){",
            "    var href=(link.getAttribute('href')||'').trim();",
            "    var text=normalizedText(link);",
            "    return href&&href!=='#'&&text&&text.indexOf(label)!==-1;",
            "  })||null;",
            "}",
            "function openSiteMap(event){",
            "  if(event){event.preventDefault();event.stopPropagation();}",
            "  window.location.href=siteMapHref;",
            "}",
            "document.addEventListener('click',function(event){",
            "  if(hasModifier(event)){return;}",
            "  var target=event.target;",
            "  if(!target||!target.closest){return;}",
            "  var button=target.closest('button');",
            "  if(button){",
            "    var parentLink=button.closest('a[href]');",
            "    if(parentLink&&navigateToLink(parentLink,event)){return;}",
            "    var buttonLabel=normalizedText(button);",
            "    var matchingLink=findLinkByLabel(buttonLabel);",
            "    if(matchingLink&&navigateToLink(matchingLink,event)){return;}",
            "    var label=((button.getAttribute('aria-label')||button.textContent||'')+' '+(button.className||'')).toLowerCase();",
            "    if(label.indexOf('toggle navigation')!==-1||label.indexOf('navbar-toggler')!==-1){openSiteMap(event);return;}",
            "  }",
            "  var link=target.closest('a[href]');",
            "  if(!link){return;}",
            "  var href=(link.getAttribute('href')||'').trim().toLowerCase();",
            "  if(href==='#'||href.indexOf('javascript:')===0){openSiteMap(event);}",
            "},true);",
            "})();",
            "</script>",
        ]
    )


def inject_offline_navigation_helper(text: str, site_map_href: str) -> str:
    if 'data-web-evidence-offline-helper="1"' in text:
        return text
    helper = offline_navigation_helper(site_map_href)
    body_match = re.search(r"</body\s*>", text, flags=re.I)
    if body_match:
        return text[: body_match.start()] + helper + text[body_match.start() :]
    return text + "\n" + helper + "\n"


def rewrite_anchor_links_for_offline(
    text: str,
    current_path: Path,
    current_url: str,
    mirror_root: Path,
    config: CaptureConfig,
    placeholders: Dict[Path, str],
) -> str:
    def rewrite(match: re.Match) -> str:
        prefix = match.group("prefix")
        quote_char = match.group("quote")
        href = match.group("href")
        stripped = href.strip()
        if not stripped or stripped.startswith("#"):
            return match.group(0)
        absolute = normalize_url(stripped, current_url)
        if not absolute:
            return match.group(0)
        if not same_domain(absolute, config.allowed_domains) or is_download_url(absolute):
            return match.group(0)
        target_path = local_page_path(mirror_root, absolute)
        if not target_path.exists():
            target_path = not_captured_page_path(mirror_root, absolute)
            placeholders.setdefault(target_path, absolute)
        return f"{prefix}{quote_char}{relative_link(current_path, target_path)}{quote_char}"

    for tag in ("a", "area"):
        pattern = re.compile(
            rf"(?P<prefix><{tag}\b[^>]*?\bhref\s*=\s*)(?P<quote>['\"])(?P<href>.*?)(?P=quote)",
            flags=re.I | re.S,
        )
        text = pattern.sub(rewrite, text)
    return text


def mirror_records(snapshot_dir: Path, mirror_name: str) -> List[Tuple[str, str, str]]:
    records: List[Tuple[str, str, str]] = []
    if mirror_name == "rendered-mirror":
        results = read_json_file(snapshot_dir / "manifest" / "render-result.json", [])
        for item in results if isinstance(results, list) else []:
            rendered_html = item.get("rendered_html") or ""
            url = item.get("final_url") or item.get("url") or ""
            title = item.get("title") or url
            prefix = "artifacts/rendered-mirror/"
            if rendered_html.startswith(prefix) and url:
                records.append((url, rendered_html[len(prefix) :], title))
    else:
        capture = read_json_file(snapshot_dir / "manifest" / "capture-result.json", {}) or {}
        for item in capture.get("captured_pages", []) if isinstance(capture, dict) else []:
            local_path = item.get("local_path") or ""
            url = item.get("final_url") or item.get("url") or ""
            title = item.get("title") or url
            prefix = "artifacts/mirror/"
            if local_path.startswith(prefix) and url:
                records.append((url, local_path[len(prefix) :], title))
    seen = set()
    deduped = []
    for url, path, title in records:
        key = (url, path)
        if key not in seen:
            seen.add(key)
            deduped.append((url, path, title))
    return sorted(deduped, key=lambda item: item[0])


def write_offline_site_map(mirror_root: Path, records: List[Tuple[str, str, str]], title: str) -> None:
    if not mirror_root.exists():
        return
    items = []
    for url, path, page_title in records:
        target = mirror_root / path
        href = relative_link(mirror_root / "_site-map.html", target) if target.exists() else html.escape(path)
        label = page_title or url
        items.append(
            f'<li><a href="{html.escape(href)}">{html.escape(label)}</a><br><code>{html.escape(url)}</code></li>'
        )
    if not items:
        items.append("<li>No captured pages were listed for this mirror.</li>")
    site_map = "\n".join(
        [
            "<!doctype html>",
            '<meta charset="utf-8">',
            f"<title>{html.escape(title)}</title>",
            '<style>body{font-family:system-ui,sans-serif;max-width:980px;margin:40px auto;padding:0 24px;line-height:1.5;color:#111827}li{margin:0 0 12px}code{font-size:.9em;color:#4b5563;word-break:break-all}a{color:#1d4ed8}</style>',
            f"<h1>{html.escape(title)}</h1>",
            "<p>This static site map lists captured pages without relying on the original site's JavaScript menus, dropdowns, or search widgets.</p>",
            '<p><a href="index.html">Open mirror home page</a></p>',
            "<ol>",
            *items,
            "</ol>",
            "",
        ]
    )
    (mirror_root / "_site-map.html").write_text(site_map, encoding="utf-8")


def prepare_offline_navigation(snapshot_dir: Path, config: CaptureConfig) -> Dict[str, object]:
    summary: Dict[str, object] = {"mirrors": {}}
    for mirror_name, title in [("rendered-mirror", "Rendered Mirror Site Map"), ("mirror", "Static Mirror Site Map")]:
        mirror_root = snapshot_dir / "artifacts" / mirror_name
        if not mirror_root.exists():
            continue
        records = mirror_records(snapshot_dir, mirror_name)
        write_offline_site_map(mirror_root, records, title)
        placeholders: Dict[Path, str] = {}
        for page_path in sorted(mirror_root.rglob("*.html")):
            if page_path.name == "_site-map.html":
                continue
            current_url = local_url_for_page(mirror_root, page_path, config.target_url)
            text = page_path.read_text(encoding="utf-8", errors="ignore")
            rewritten = rewrite_anchor_links_for_offline(text, page_path, current_url, mirror_root, config, placeholders)
            rewritten = inject_offline_navigation_helper(
                rewritten,
                relative_link(page_path, mirror_root / "_site-map.html"),
            )
            if rewritten != text:
                page_path.write_text(rewritten, encoding="utf-8", errors="replace")
        for target_path, url in sorted(placeholders.items(), key=lambda item: item[0].as_posix()):
            if target_path.exists():
                continue
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(
                not_captured_page(url, relative_link(target_path, mirror_root / "_site-map.html")),
                encoding="utf-8",
            )
        summary["mirrors"][mirror_name] = {
            "captured_pages_listed": len(records),
            "placeholder_pages_created": len(placeholders),
            "site_map": f"artifacts/{mirror_name}/_site-map.html",
        }
    write_json(snapshot_dir / "manifest" / "offline-navigation.json", summary)
    return summary


def completed_stages(stage: str) -> List[str]:
    if stage in STAGE_ORDER:
        return STAGE_ORDER[: STAGE_ORDER.index(stage) + 1]
    return [stage]


def snapshot_root_for_run(config: CaptureConfig, run_dir: Path) -> Tuple[Path, str, str]:
    site = site_slug(config.target_url, config.case_slug)
    run_stamp = run_dir.name
    return Path("snapshots") / site / run_stamp, site, run_stamp


def write_status_files(snapshot_dir: Path, config: CaptureConfig, stage: str, final: bool) -> Dict[str, object]:
    status = {
        "archives_created": final,
        "completed_stages": completed_stages(stage),
        "final": final,
        "run": snapshot_dir.name,
        "snapshot_dir": snapshot_dir.as_posix(),
        "stage": stage,
        "target_url": config.target_url,
        "updated_utc": utc_now(),
    }
    write_json(snapshot_dir / "manifest" / "snapshot-status.json", status)
    state = "final" if final else "partial"
    archive_note = (
        "The complete snapshot ZIP and website HTML ZIP have been generated."
        if final
        else "Archive ZIP files are created only by the final publishing job."
    )
    lines = [
        "# Snapshot Status",
        "",
        f"Status: `{state}`",
        "",
        f"Completed stage: `{stage}`",
        "",
        f"Updated UTC: `{status['updated_utc']}`",
        "",
        f"Target URL: `{config.target_url}`",
        "",
        "## How To Use This Folder",
        "",
        "Open `START-HERE.md` when present. Open `report/report.md` after the report stage has completed.",
        "",
        archive_note,
        "",
        "## Completed Stages",
        "",
        *[f"- `{item}`" for item in status["completed_stages"]],
        "",
        "Folders from later stages can be absent or incomplete until the workflow reaches those stages.",
        "",
    ]
    (snapshot_dir / "SNAPSHOT-STATUS.md").write_text("\n".join(lines), encoding="utf-8")
    return status


def write_readme_if_missing(path: Path, title: str, body: str) -> None:
    path.mkdir(parents=True, exist_ok=True)
    readme = path / "README.md"
    if not readme.exists():
        readme.write_text(f"# {title}\n\n{body.strip()}\n", encoding="utf-8")


def write_partial_guides(snapshot_dir: Path, config: CaptureConfig, site: str, run_stamp: str, final: bool) -> None:
    full_zip = f"{site}-{run_stamp}.zip"
    browse_zip = f"{site}-{run_stamp}-website-html.zip"
    if not (snapshot_dir / "START-HERE.md").exists():
        text = f"""# Start Here

This snapshot preserves a public website capture for:

`{config.target_url}`

Run folder:

`{run_stamp}`

## Current State

Open `SNAPSHOT-STATUS.md` first. This snapshot may be partial while the workflow is still running.

## What To Open

1. Open `report/report.md` after the report stage completes.
2. Open `manifest/` for machine-readable records.
3. Open `validation/validation.json` after validation completes.
4. Open `hashes/files.sha256` to verify file integrity when hashes are available.

## Downloads

- Complete snapshot ZIP: `{full_zip}`
- Captured website HTML ZIP: `{browse_zip}`

These ZIP files are generated by the final publishing job.

This is technical preservation support, not legal advice. Captured material can include copyrighted content, personal data, tracking metadata, or third-party content.
"""
        (snapshot_dir / "START-HERE.md").write_text(text, encoding="utf-8")
    write_readme_if_missing(
        snapshot_dir,
        "Snapshot Overview",
        "Start with `SNAPSHOT-STATUS.md`, then `START-HERE.md`. This folder is updated progressively by the workflow, so early snapshots can be partial until the final job completes.",
    )
    write_readme_if_missing(
        snapshot_dir / "manifest",
        "Manifests",
        "Machine-readable configuration, inventory, capture, render, packaging, validation, summary, and snapshot status records.",
    )
    write_readme_if_missing(
        snapshot_dir / "validation",
        "Validation",
        "Validation records appear after the validation stage. Until then, this folder can be empty or incomplete.",
    )
    write_readme_if_missing(
        snapshot_dir / "hashes",
        "Hashes",
        "SHA-256 hash lists for the snapshot. The generated hash list and file manifest are excluded from their own calculation.",
    )
    write_readme_if_missing(
        snapshot_dir / "logs",
        "Logs",
        "Structured tool logs and workflow logs when available. These logs document operational sequence, timestamps, retries, warnings, and errors.",
    )
    write_readme_if_missing(
        snapshot_dir / "artifacts",
        "Artifacts",
        "Captured website evidence appears here as stages complete, including mirrors, screenshots, PDFs, SingleFile exports, WARC, WACZ, and browser/network observations.",
    )
    if final:
        return
    write_readme_if_missing(
        snapshot_dir / "report",
        "Reports",
        "Reports are generated near the end of the workflow. This folder can be empty before the report stage completes.",
    )


def singlefile_links(snapshot_dir: Path) -> List[Tuple[str, str]]:
    results = read_json_file(snapshot_dir / "manifest" / "singlefile-result.json", [])
    links = []
    for item in results if isinstance(results, list) else []:
        output = item.get("output") or ""
        if output and item.get("exists"):
            links.append((item.get("url") or output, f"singlefile/{Path(output).name}"))
    return links


def create_website_archive(snapshot_dir: Path, config: CaptureConfig, site: str, run_stamp: str) -> Path:
    website_archive_path = snapshot_dir / f"{site}-{run_stamp}-website-html.zip"
    links = singlefile_links(snapshot_dir)
    rendered_exists = (snapshot_dir / "artifacts" / "rendered-mirror" / "index.html").exists()
    static_exists = (snapshot_dir / "artifacts" / "mirror" / "index.html").exists()
    singlefile_index = "\n".join(
        [
            "<!doctype html>",
            '<meta charset="utf-8">',
            "<title>SingleFile Captures</title>",
            "<h1>SingleFile Captures</h1>",
            "<p>These pages are self-contained HTML exports when SingleFile succeeded. They are listed separately from mirror navigation.</p>",
            "<ol>",
            *[f'<li><a href="{html.escape(path)}">{html.escape(url)}</a></li>' for url, path in links],
            "</ol>",
            "",
        ]
    )
    website_index = "\n".join(
        [
            "<!doctype html>",
            '<meta charset="utf-8">',
            "<title>Captured Website HTML</title>",
            '<style>body{font-family:system-ui,sans-serif;max-width:820px;margin:48px auto;padding:0 24px;line-height:1.55;color:#111827}.actions{display:grid;gap:12px;margin:24px 0}.actions a{display:block;border:1px solid #d1d5db;border-radius:8px;padding:14px 16px;text-decoration:none;color:#1d4ed8}code{background:#f3f4f6;padding:2px 4px;border-radius:4px}</style>',
            "<h1>Captured Website HTML</h1>",
            f"<p>This ZIP contains local browsing files for <code>{html.escape(config.target_url)}</code>.</p>",
            '<div class="actions">',
            '<a href="open-rendered-mirror.html"><strong>Open rendered mirror</strong><br>Best first choice for browser-observed pages.</a>',
            '<a href="site-map.html"><strong>Open offline site map</strong><br>Use this static page list when menus, dropdowns, or scripted controls do not work offline.</a>',
            '<a href="open-static-mirror.html"><strong>Open static mirror</strong><br>Fallback for server-returned HTML.</a>',
            '<a href="singlefile-index.html"><strong>Open SingleFile index</strong><br>Self-contained individual page exports when available.</a>',
            "</div>",
            "<p>Same-domain links inside the rendered mirror are rewritten to local files when the target page was captured. Links to same-domain pages that were not captured open a local explanation page instead of a blank browser page.</p>",
            "<p>Dropdowns, hamburger controls, and buttons that depend on the original site's runtime scripts are given an offline fallback to the site map or to their enclosing link when one is present.</p>",
            "",
        ]
    )
    sitemap_launcher = "\n".join(
        [
            "<!doctype html>",
            '<meta charset="utf-8">',
            "<title>Offline Site Map</title>",
            '<meta http-equiv="refresh" content="0; url=rendered-mirror/_site-map.html">',
            '<p>Open <a href="rendered-mirror/_site-map.html">rendered-mirror/_site-map.html</a>.</p>',
            "",
        ]
    )
    browse_readme = "\n".join(
        [
            "# Captured Website HTML",
            "",
            "This ZIP contains only the local HTML browsing portion of the snapshot for:",
            "",
            config.target_url,
            "",
            "## What To Open",
            "",
            "1. Unzip this file.",
            "2. Open `index.html` in a browser.",
            "3. From there, open the rendered mirror, the offline site map, the static mirror, or SingleFile exports.",
            "4. If a menu, dropdown, or scripted control does not work offline, open `site-map.html` to choose a captured page from a static list.",
            "5. In the rendered mirror, offline helper logic routes dropdown toggles and navigation buttons to the site map or to their enclosing captured link when possible.",
            "",
            "The rendered mirror reflects browser-observed HTML from the GitHub-hosted runner.",
            "The static mirror reflects public HTTP HTML with executable scripts disabled for offline review.",
            "SingleFile pages are usually the easiest individual pages to open offline, but they are listed one page at a time.",
            "Same-domain links in the rendered mirror are rewritten to local files where the target page was captured.",
            "",
            f"This ZIP is for navigation and review. For the complete evidence package, use `{site}-{run_stamp}.zip` or the expanded snapshot folder.",
            "",
        ]
    )
    rendered_launcher = "\n".join(
        [
            "<!doctype html>",
            '<meta charset="utf-8">',
            "<title>Open Rendered Mirror</title>",
            '<meta http-equiv="refresh" content="0; url=rendered-mirror/index.html">',
            '<p>Open <a href="rendered-mirror/index.html">rendered-mirror/index.html</a>.</p>',
            "",
        ]
    )
    static_launcher = "\n".join(
        [
            "<!doctype html>",
            '<meta charset="utf-8">',
            "<title>Open Static Mirror</title>",
            '<meta http-equiv="refresh" content="0; url=static-mirror/index.html">',
            '<p>Open <a href="static-mirror/index.html">static-mirror/index.html</a>.</p>',
            "",
        ]
    )
    with zipfile.ZipFile(website_archive_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        archive.writestr("README.md", browse_readme)
        archive.writestr("index.html", website_index)
        archive.writestr("open-rendered-mirror.html", rendered_launcher)
        archive.writestr("open-static-mirror.html", static_launcher)
        archive.writestr("site-map.html", sitemap_launcher)
        archive.writestr("singlefile-index.html", singlefile_index)
        archive.writestr(
            "availability.json",
            json.dumps(
                {
                    "rendered_mirror_index": rendered_exists,
                    "singlefile_pages": len(links),
                    "static_mirror_index": static_exists,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
        )
        add_tree(archive, snapshot_dir / "artifacts" / "rendered-mirror", "rendered-mirror")
        add_tree(archive, snapshot_dir / "artifacts" / "mirror", "static-mirror")
        add_tree(archive, snapshot_dir / "artifacts" / "singlefile", "singlefile")
    return website_archive_path


def create_full_archive(snapshot_dir: Path, site: str, run_stamp: str) -> Path:
    archive_path = snapshot_dir / f"{site}-{run_stamp}.zip"
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for file_path in sorted(snapshot_dir.rglob("*")):
            if file_path == archive_path or not file_path.is_file():
                continue
            archive.write(file_path, file_path.relative_to(snapshot_dir).as_posix())
    return archive_path


def external_archive_dir(site: str, run_stamp: str) -> Path:
    return Path("snapshot-archives") / site / run_stamp


def archive_record(path: Path, external_dir: Path, max_git_archive_bytes: int) -> Dict[str, object]:
    digest = sha256_file(path)
    size = path.stat().st_size
    record: Dict[str, object] = {
        "filename": path.name,
        "sha256": digest,
        "size_bytes": size,
        "committed_to_snapshot": True,
        "snapshot_path": path.name,
        "external_path": "",
        "git_omission_reason": "",
    }
    if size > max_git_archive_bytes:
        external_dir.mkdir(parents=True, exist_ok=True)
        external_path = external_dir / path.name
        if external_path.exists():
            external_path.unlink()
        shutil.move(str(path), str(external_path))
        record.update(
            {
                "committed_to_snapshot": False,
                "snapshot_path": "",
                "external_path": external_path.as_posix(),
                "git_omission_reason": (
                    f"Archive is larger than the configured Git commit threshold "
                    f"({max_git_archive_bytes} bytes) and GitHub rejects individual Git files above "
                    f"{GITHUB_GIT_FILE_LIMIT_BYTES} bytes."
                ),
            }
        )
    return record


def write_archive_notes(snapshot_dir: Path, archive_details: Dict[str, Dict[str, object]]) -> None:
    lines = [
        "# Snapshot Archives",
        "",
        "This file explains where the generated ZIP archives are stored.",
        "",
        "The expanded snapshot directory is committed to Git. Large ZIP archives may be stored outside the Git tree because GitHub rejects individual Git files above 100 MB.",
        "",
        "| Archive | Size bytes | SHA-256 | Committed in this snapshot | External path |",
        "| --- | ---: | --- | --- | --- |",
    ]
    for key in ["complete_snapshot_zip", "website_html_zip"]:
        item = archive_details[key]
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{item['filename']}`",
                    str(item["size_bytes"]),
                    f"`{item['sha256']}`",
                    "`yes`" if item["committed_to_snapshot"] else "`no`",
                    f"`{item['external_path']}`" if item["external_path"] else "",
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "If an external path is listed, the workflow uploads that file from `snapshot-archives/` as a workflow artifact and, when configured, as a release asset. Use the SHA-256 values above to verify downloaded archives.",
            "",
        ]
    )
    (snapshot_dir / "ARCHIVES.md").write_text("\n".join(lines), encoding="utf-8")
    start_here = snapshot_dir / "START-HERE.md"
    if start_here.exists():
        text = start_here.read_text(encoding="utf-8")
        marker = "## Archive Download Details"
        if marker not in text:
            text = text.rstrip() + "\n\n" + marker + "\n\nOpen `ARCHIVES.md` for archive sizes, SHA-256 values, and external download paths when ZIP files are too large to commit to Git.\n"
            start_here.write_text(text, encoding="utf-8")


def write_archive_manifest(
    snapshot_dir: Path,
    archive_path: Path,
    website_archive_path: Path,
    site: str,
    run_stamp: str,
    max_git_archive_bytes: int,
) -> Dict[str, Dict[str, object]]:
    external_dir = external_archive_dir(site, run_stamp)
    archive_details = {
        "complete_snapshot_zip": archive_record(archive_path, external_dir, max_git_archive_bytes),
        "website_html_zip": archive_record(website_archive_path, external_dir, max_git_archive_bytes),
    }
    archive_hash_path = snapshot_dir / "hashes" / "snapshot-archive.sha256"
    archive_hash_path.parent.mkdir(parents=True, exist_ok=True)
    archive_hash_path.write_text(
        (
            f"{archive_details['complete_snapshot_zip']['sha256']}  {archive_details['complete_snapshot_zip']['filename']}\n"
            f"{archive_details['website_html_zip']['sha256']}  {archive_details['website_html_zip']['filename']}\n"
        ),
        encoding="utf-8",
    )
    write_json(
        snapshot_dir / "manifest" / "snapshot-archives.json",
        {
            "archives": archive_details,
            "complete_snapshot_zip": archive_details["complete_snapshot_zip"]["filename"],
            "complete_snapshot_zip_committed_to_snapshot": archive_details["complete_snapshot_zip"]["committed_to_snapshot"],
            "complete_snapshot_zip_external_path": archive_details["complete_snapshot_zip"]["external_path"],
            "complete_snapshot_zip_sha256": archive_details["complete_snapshot_zip"]["sha256"],
            "complete_snapshot_zip_size_bytes": archive_details["complete_snapshot_zip"]["size_bytes"],
            "git_file_size_limit_bytes": GITHUB_GIT_FILE_LIMIT_BYTES,
            "large_archive_commit_threshold_bytes": max_git_archive_bytes,
            "large_archive_policy": "Archives larger than the configured threshold are moved to snapshot-archives/ and are not committed to Git.",
            "website_html_zip": archive_details["website_html_zip"]["filename"],
            "website_html_zip_committed_to_snapshot": archive_details["website_html_zip"]["committed_to_snapshot"],
            "website_html_zip_external_path": archive_details["website_html_zip"]["external_path"],
            "website_html_zip_note": "Smaller package for browsing captured HTML locally.",
            "website_html_zip_sha256": archive_details["website_html_zip"]["sha256"],
            "website_html_zip_size_bytes": archive_details["website_html_zip"]["size_bytes"],
        },
    )
    write_archive_notes(snapshot_dir, archive_details)
    return archive_details


def publish_snapshot(
    config: CaptureConfig,
    run_dir: Path,
    stage: str,
    final: bool = False,
    max_git_archive_bytes: int = DEFAULT_ARCHIVE_COMMIT_LIMIT_BYTES,
) -> Dict[str, object]:
    snapshot_dir, site, run_stamp = snapshot_root_for_run(config, run_dir)
    snapshot_dir.parent.mkdir(parents=True, exist_ok=True)
    if snapshot_dir.exists():
        shutil.rmtree(snapshot_dir)
    shutil.copytree(run_dir, snapshot_dir)
    (snapshot_dir.parent / "latest.txt").write_text(f"{run_stamp}\n", encoding="utf-8")
    status = write_status_files(snapshot_dir, config, stage, final)
    write_partial_guides(snapshot_dir, config, site, run_stamp, final)
    prepare_offline_navigation(snapshot_dir, config)
    archive_paths: Dict[str, str] = {}
    if final:
        website_archive_path = create_website_archive(snapshot_dir, config, site, run_stamp)
        write_hashes(snapshot_dir)
        archive_path = create_full_archive(snapshot_dir, site, run_stamp)
        archive_details = write_archive_manifest(
            snapshot_dir,
            archive_path,
            website_archive_path,
            site,
            run_stamp,
            max_git_archive_bytes,
        )
        archive_paths = {
            key: str(value.get("snapshot_path") or value.get("external_path") or value.get("filename"))
            for key, value in archive_details.items()
        }
    rows = write_hashes(snapshot_dir)
    return {
        "archives": archive_paths,
        "hashed_files": len(rows),
        "snapshot_dir": snapshot_dir.as_posix(),
        "status": status,
    }
