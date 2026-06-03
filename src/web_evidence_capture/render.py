from pathlib import Path
from typing import Dict, List

from .config import CaptureConfig
from .logging_utils import local_now, log_event, read_json, utc_now, write_json
from .mirror import disable_executable_scripts, local_page_path, normalize_url


COOKIE_DENY_SELECTORS = [
    "#CybotCookiebotDialogBodyButtonDecline",
    "button:has-text('Deny')",
    "button:has-text('Reject')",
    "button:has-text('Decline')",
]


def selected_urls(run_dir: Path, config: CaptureConfig) -> List[str]:
    capture = read_json(run_dir / "manifest" / "capture-result.json", {}) or {}
    urls = [item.get("final_url") or item.get("url") for item in capture.get("captured_pages", [])]
    if not urls:
        inventory = read_json(run_dir / "manifest" / "url-inventory.json", {}) or {}
        urls = inventory.get("urls", []) or [config.target_url]
    seen = set()
    result = []
    for url in urls:
        normalized = normalize_url(url, config.target_url)
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result[: config.max_pages or None]


def handle_cookie_choice(page, choice: str) -> Dict[str, object]:
    result = {"choice": choice, "button_clicked": "", "error": "", "timestamp_local": local_now(), "timestamp_utc": utc_now()}
    if choice == "none":
        return result
    if choice != "deny":
        result["error"] = f"Unsupported cookie choice: {choice}"
        return result
    for selector in COOKIE_DENY_SELECTORS:
        try:
            locator = page.locator(selector)
            if locator.count() and locator.first.is_visible(timeout=1500):
                locator.first.click()
                page.wait_for_timeout(1000)
                result["button_clicked"] = selector
                return result
        except Exception as exc:
            result["error"] = str(exc)
    return result


def run_render(config: CaptureConfig, run_dir: Path) -> List[Dict[str, object]]:
    urls = selected_urls(run_dir, config)
    results: List[Dict[str, object]] = []
    log_event(run_dir, "render", "start", urls=len(urls), cookie_choice=config.cookie_choice)
    if config.dry_run:
        for url in urls:
            results.append({"url": url, "dry_run": True, "attempts": [], "error": ""})
        write_json(run_dir / "manifest" / "render-result.json", results)
        return results

    from playwright.sync_api import sync_playwright

    screenshot_root = run_dir / "artifacts" / "screenshots"
    pdf_root = run_dir / "artifacts" / "pdf"
    rendered_mirror_root = run_dir / "artifacts" / "rendered-mirror"
    screenshot_root.mkdir(parents=True, exist_ok=True)
    pdf_root.mkdir(parents=True, exist_ok=True)
    rendered_mirror_root.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, args=["--disable-dev-shm-usage"])
        context = browser.new_context(viewport={"width": 1440, "height": 1000}, user_agent=config.user_agent)
        page = context.new_page()
        cookie_done = False
        for index, url in enumerate(urls, start=1):
            slug = f"{index:03d}-{Path(normalize_url(url, config.target_url) or url).name or 'homepage'}"
            screenshot = screenshot_root / f"{slug}.png"
            pdf = pdf_root / f"{slug}.pdf"
            rendered_html = local_page_path(rendered_mirror_root, url)
            attempts = []
            record = {
                "url": url,
                "final_url": "",
                "title": "",
                "status": "",
                "screenshot": screenshot.relative_to(run_dir).as_posix(),
                "pdf": pdf.relative_to(run_dir).as_posix(),
                "rendered_html": rendered_html.relative_to(run_dir).as_posix(),
                "attempts": attempts,
                "error": "",
            }
            wait_modes = ["networkidle"] + ["load"] * config.render_retries
            for attempt_index, wait_until in enumerate(wait_modes, start=1):
                attempt = {"attempt": attempt_index, "wait_until": wait_until, "timestamp_local": local_now(), "resolved": False, "error": ""}
                try:
                    response = page.goto(url, wait_until=wait_until, timeout=60000)
                    page.wait_for_timeout(1500)
                    if not cookie_done:
                        record["cookie_choice_result"] = handle_cookie_choice(page, config.cookie_choice)
                        cookie_done = True
                    record["final_url"] = page.url
                    record["title"] = page.title()
                    record["status"] = str(response.status if response else "")
                    page.screenshot(path=str(screenshot), full_page=True, type="png")
                    page.pdf(path=str(pdf), format="A4", print_background=True)
                    rendered_html.parent.mkdir(parents=True, exist_ok=True)
                    rendered_html.write_text(disable_executable_scripts(page.content()), encoding="utf-8", errors="replace")
                    if normalize_url(page.url, config.target_url).rstrip("/") == normalize_url(config.target_url, config.target_url).rstrip("/"):
                        index_path = rendered_mirror_root / "index.html"
                        if rendered_html != index_path:
                            index_path.write_text(rendered_html.read_text(encoding="utf-8", errors="ignore"), encoding="utf-8", errors="replace")
                    attempt["resolved"] = True
                    attempts.append(attempt)
                    record["error"] = ""
                    break
                except Exception as exc:
                    attempt["error"] = str(exc)
                    attempts.append(attempt)
                    record["error"] = str(exc)
                    log_event(run_dir, "render", "attempt_failed", url=url, attempt=attempt_index, wait_until=wait_until, error=str(exc))
            results.append(record)
            log_event(run_dir, "render", "rendered", url=url, status=record["status"], error=record["error"])
        context.close()
        browser.close()
    write_json(run_dir / "manifest" / "render-result.json", results)
    log_event(run_dir, "render", "complete", rendered=len(results), retries=sum(len(item["attempts"]) - 1 for item in results if item.get("attempts")))
    return results
