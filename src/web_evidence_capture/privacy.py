from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List
from urllib.parse import parse_qs, urlparse

from .config import CaptureConfig
from .logging_utils import local_now, log_event, utc_now, write_json


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
    try:
        post_data_length = len(request.post_data or "")
    except Exception:
        post_data_length = 0
    return {
        "timestamp_local": local_now(),
        "timestamp_utc": utc_now(),
        "url": request.url,
        "domain": parsed.netloc,
        "method": request.method,
        "resource_type": request.resource_type,
        "query_keys": sorted(query.keys()),
        "post_data_length": post_data_length,
        "status": response.status if response else None,
        "content_type": response.headers.get("content-type", "") if response else "",
    }


def run_privacy(config: CaptureConfig, run_dir: Path) -> Dict[str, object]:
    log_event(run_dir, "privacy", "start", target_url=config.target_url)
    if config.dry_run:
        result = {"dry_run": True, "network_event_count": 0, "third_party_domains": {}, "cookies_after_choice": []}
        write_json(run_dir / "manifest" / "privacy-result.json", result)
        return result

    from playwright.sync_api import sync_playwright

    network_records: List[Dict[str, object]] = []
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
        page.goto(config.target_url, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(2500)
        before = context.cookies()
        from .render import handle_cookie_choice

        choice = handle_cookie_choice(page, config.cookie_choice)
        page.wait_for_timeout(1500)
        after = context.cookies()
        browser.close()

    privacy_dir = run_dir / "artifacts" / "privacy"
    privacy_dir.mkdir(parents=True, exist_ok=True)
    write_json(privacy_dir / "cookies-before-choice-summary.json", cookie_summary(before))
    write_json(privacy_dir / "cookies-after-choice-summary.json", cookie_summary(after))
    domain_counter = Counter(record["domain"] for record in network_records if record.get("domain"))
    query_keys = defaultdict(set)
    for record in network_records:
        for key in record.get("query_keys", []):
            query_keys[record.get("domain", "")].add(key)
    result = {
        "target_url": config.target_url,
        "cookie_choice_result": choice,
        "cookies_before_choice_count": len(before),
        "cookies_after_choice_count": len(after),
        "network_event_count": len(network_records),
        "domains_observed": dict(domain_counter.most_common()),
        "query_keys_by_domain": {domain: sorted(keys) for domain, keys in query_keys.items()},
        "note": "Cookie values and raw request bodies are not written by default.",
        "completed_local": local_now(),
        "completed_utc": utc_now(),
    }
    write_json(run_dir / "manifest" / "privacy-result.json", result)
    log_event(run_dir, "privacy", "complete", network_events=len(network_records), domains=len(domain_counter))
    return result

