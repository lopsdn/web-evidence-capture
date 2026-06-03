import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List
from urllib.parse import parse_qs, urlparse

from .config import CaptureConfig
from .logging_utils import local_now, log_event, utc_now, write_json
from .render import handle_cookie_choice, selected_urls


def cookie_summary(cookies: List[Dict[str, object]]) -> List[Dict[str, object]]:
    return [
        {
            "name": cookie.get("name"),
            "domain": cookie.get("domain"),
            "path": cookie.get("path"),
            "expires": cookie.get("expires"),
            "httpOnly": cookie.get("httpOnly"),
            "secure": cookie.get("secure"),
            "sameSite": cookie.get("sameSite"),
            "value_length": len(str(cookie.get("value", ""))),
        }
        for cookie in cookies
    ]


def request_summary(request, response=None) -> Dict[str, object]:
    parsed = urlparse(request.url)
    query = parse_qs(parsed.query)
    post_data_length = 0
    post_data = ""
    try:
        post_data = request.post_data or ""
        post_data_length = len(post_data)
    except Exception:
        post_data_length = 0
    request_headers = {}
    response_headers = {}
    try:
        request_headers = dict(request.headers)
    except Exception:
        request_headers = {}
    if response:
        try:
            response_headers = dict(response.headers)
        except Exception:
            response_headers = {}
    return {
        "timestamp_local": local_now(),
        "timestamp_utc": utc_now(),
        "url": request.url,
        "domain": parsed.netloc,
        "method": request.method,
        "resource_type": request.resource_type,
        "request_headers": request_headers,
        "query_keys": sorted(query.keys()),
        "query": query,
        "post_data": post_data,
        "post_data_length": post_data_length,
        "status": response.status if response else None,
        "content_type": response.headers.get("content-type", "") if response else "",
        "response_headers": response_headers,
    }


def write_jsonl(path: Path, rows: List[Dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def run_privacy(config: CaptureConfig, run_dir: Path) -> Dict[str, object]:
    log_event(run_dir, "privacy", "start", target_url=config.target_url)
    if config.dry_run:
        result = {"dry_run": True, "network_event_count": 0, "third_party_domains": {}, "cookies_after_choice": []}
        write_json(run_dir / "manifest" / "privacy-result.json", result)
        return result

    from playwright.sync_api import sync_playwright

    network_records: List[Dict[str, object]] = []
    console_records: List[Dict[str, object]] = []
    page_error_records: List[Dict[str, object]] = []
    urls = selected_urls(run_dir, config)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 1000}, user_agent=config.user_agent)
        page = context.new_page()

        def on_request(request):
            network_records.append(request_summary(request))

        def on_response(response):
            network_records.append(request_summary(response.request, response=response))

        page.on("request", on_request)
        page.on("response", on_response)
        page.on(
            "console",
            lambda message: console_records.append(
                {
                    "timestamp_local": local_now(),
                    "timestamp_utc": utc_now(),
                    "type": message.type,
                    "text": message.text,
                    "location": message.location,
                }
            ),
        )
        page.on(
            "pageerror",
            lambda exc: page_error_records.append(
                {
                    "timestamp_local": local_now(),
                    "timestamp_utc": utc_now(),
                    "error": str(exc),
                }
            ),
        )
        before = []
        after = []
        choice = {"choice": config.cookie_choice, "button_clicked": "", "error": "", "timestamp_local": local_now(), "timestamp_utc": utc_now()}
        for index, url in enumerate(urls, start=1):
            try:
                page.goto(url, wait_until="networkidle", timeout=60000)
            except Exception as exc:
                log_event(run_dir, "privacy", "navigation_failed", url=url, error=str(exc))
                try:
                    page.goto(url, wait_until="load", timeout=60000)
                except Exception as fallback_exc:
                    log_event(run_dir, "privacy", "navigation_fallback_failed", url=url, error=str(fallback_exc))
                    continue
            page.wait_for_timeout(1500)
            if index == 1:
                before = context.cookies()
                choice = handle_cookie_choice(page, config.cookie_choice)
                page.wait_for_timeout(1500)
        after = context.cookies()
        storage_state = context.storage_state()
        browser.close()

    privacy_dir = run_dir / "artifacts" / "privacy"
    privacy_dir.mkdir(parents=True, exist_ok=True)
    write_json(privacy_dir / "cookies-before-choice.json", before)
    write_json(privacy_dir / "cookies-after-choice.json", after)
    write_json(privacy_dir / "cookies-before-choice-summary.json", cookie_summary(before))
    write_json(privacy_dir / "cookies-after-choice-summary.json", cookie_summary(after))
    write_json(privacy_dir / "storage-state-after-choice.json", storage_state)
    write_json(privacy_dir / "network-events.json", network_records)
    write_jsonl(privacy_dir / "network-events.jsonl", network_records)
    write_json(privacy_dir / "console-events.json", console_records)
    write_jsonl(privacy_dir / "console-events.jsonl", console_records)
    write_json(privacy_dir / "page-errors.json", page_error_records)
    write_jsonl(privacy_dir / "page-errors.jsonl", page_error_records)
    domain_counter = Counter(record["domain"] for record in network_records if record.get("domain"))
    query_keys = defaultdict(set)
    for record in network_records:
        for key in record.get("query_keys", []):
            query_keys[record.get("domain", "")].add(key)
    result = {
        "target_url": config.target_url,
        "cookie_choice_result": choice,
        "pages_visited": len(urls),
        "cookies_before_choice_count": len(before),
        "cookies_after_choice_count": len(after),
        "network_event_count": len(network_records),
        "console_event_count": len(console_records),
        "page_error_count": len(page_error_records),
        "domains_observed": dict(domain_counter.most_common()),
        "query_keys_by_domain": {domain: sorted(keys) for domain, keys in query_keys.items()},
        "artifacts": {
            "cookies_before_choice": "artifacts/privacy/cookies-before-choice.json",
            "cookies_after_choice": "artifacts/privacy/cookies-after-choice.json",
            "storage_state_after_choice": "artifacts/privacy/storage-state-after-choice.json",
            "network_events_json": "artifacts/privacy/network-events.json",
            "network_events_jsonl": "artifacts/privacy/network-events.jsonl",
            "console_events_jsonl": "artifacts/privacy/console-events.jsonl",
            "page_errors_jsonl": "artifacts/privacy/page-errors.jsonl",
        },
        "note": "Browser-observed cookie values, request headers, response headers, query values, and request bodies are preserved for the GitHub-hosted runner session.",
        "completed_local": local_now(),
        "completed_utc": utc_now(),
    }
    write_json(run_dir / "manifest" / "privacy-result.json", result)
    log_event(run_dir, "privacy", "complete", network_events=len(network_records), domains=len(domain_counter))
    return result
