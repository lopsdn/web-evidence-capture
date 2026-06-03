# Executive Summary

Target: `https://www.assertiveyield.com/`

Case: `assertiveyield-snapshot`

Generated: 2026-06-03T13:57:28+00:00 (2026-06-03T13:57:28+00:00)

This package preserves public website evidence only. It records URL inventory, public HTTP capture, mirror output, WARC/WACZ packaging, screenshots, PDFs, privacy summaries, manifests, hashes, validation evidence, and logs where available.

Validation status: `completed_with_warnings`

Counts:

- Inventory URLs: `3`
- Captured pages: `3`
- Rendered pages: `3`
- Render retries: `1`
- WACZ pages detected: `0`

No authentication was attempted, no accounts were created, and no forms were submitted.


# Methodology

The capture followed a staged public-only process:

1. Scope configuration and case initialization.
2. Robots and sitemap capture.
3. Public URL inventory.
4. Public HTTP capture into mirror and WARC.
5. Browser rendering for screenshots and PDFs.
6. Privacy inspection using summary metadata.
7. SingleFile export when available.
8. WACZ packaging and validation.
9. Hash manifest, validation, and report generation.

Access policy:

- Public-only capture: `true`
- Authentication attempted: `false`
- Accounts created: `false`
- Forms submitted: `false`

The static mirror is a review aid. Original HTTP responses are preserved in WARC when WARC capture is available.


# Capture Report

## Scope

- Target URL: `https://www.assertiveyield.com/`
- Allowed domains: `assertiveyield.com, www.assertiveyield.com`
- Max pages: `3`
- Cookie choice: `deny`

## Captured Pages



- `200` https://www.assertiveyield.com/ - Assertive Yield - Publishers Next-Gen Tech Platform; mirror: `artifacts/mirror/index.html`

- `200` https://www.assertiveyield.com/about-us/ - About Us; mirror: `artifacts/mirror/about-us/index.html`

- `200` https://www.assertiveyield.com/ailayouts/ - AI Layouts; mirror: `artifacts/mirror/ailayouts/index.html`



## Failures And Skips

- Inventory failures: `0`
- Capture failures: `0`
- Inventory skips: `6`
- Capture skips: `0`


# Integrity

Hash manifest:

- `manifest/file-manifest.json`
- `hashes/files.sha256`

Validation:

- Status: `completed_with_warnings`
- WARC exists: `True`
- WACZ exists: `True`
- WACZ validate exit code: `0`
- WACZ pages detected: `0`
- Mirror meaningful body exists: `True`

Generated hash files exclude `hashes/files.sha256` and `manifest/file-manifest.json` from their own hash calculation.


# Privacy Summary

The privacy inspector records summary metadata by default.

- Cookies before choice: `30`
- Cookies after choice: `17`
- Network events observed: `288`

Cookie values and raw request bodies are not written by default.


## Domains Observed


- `alb.reddit.com`: 2

- `api-eu1.hubapi.com`: 2

- `api-eu1.hubspot.com`: 2

- `api.segment.io`: 2

- `c.bing.com`: 2

- `c.clarity.ms`: 4

- `cdn.builder.io`: 34

- `cdn.jsdelivr.net`: 6

- `cdn.segment.com`: 18

- `consent.cookiebot.com`: 8

- `consentcdn.cookiebot.com`: 8

- `cta-eu1.hubspot.com`: 2

- `fonts.googleapis.com`: 6

- `fonts.gstatic.com`: 4

- `forms-eu1.hscollectedforms.net`: 2

- `j.clarity.ms`: 12

- `js-eu1.hs-analytics.net`: 2

- `js-eu1.hs-banner.com`: 2

- `js-eu1.hs-scripts.com`: 2

- `js-eu1.hsadspixel.net`: 2

- `js-eu1.hscollectedforms.net`: 2

- `js-eu1.hubspot.com`: 2

- `js-eu1.usemessages.com`: 2

- `js.intercomcdn.com`: 4

- `js.zi-scripts.com`: 4

- `perf-eu1.hsforms.com`: 2

- `pixel-config.reddit.com`: 2

- `res.cloudinary.com`: 28

- `scripts.clarity.ms`: 2

- `status.assertiveyield.com`: 6

- `track-eu1.hubspot.com`: 4

- `widget.intercom.io`: 2

- `ws.zoominfo.com`: 2

- `www.assertiveyield.com`: 88

- `www.clarity.ms`: 2

- `www.google-analytics.com`: 4

- `www.googletagmanager.com`: 6

- `www.redditstatic.com`: 2




# Limitations

This technical package is not legal advice and does not guarantee legal admissibility.

The capture reflects public content reachable during the configured capture window only. Content can differ by time, location, CDN routing, browser version, cookie state, A/B testing, third-party script behavior, and network behavior.

If captured through GitHub Actions, the capture ran from a GitHub-hosted runner. That runner environment may differ from a local browser, a target user geography, or a court-supervised collection environment.

WACZ validation and WACZ page-index completeness are separate facts. If WACZ validates but `pages_detected` is zero, review the WARC/WACZ package and logs before relying on replay completeness.


# Anomalies / Retries


- Render retry for `https://www.assertiveyield.com/`; resolved: `True`.

- Warning: `wacz_zero_pages_detected`.

- Warning: `render_retries_recorded`.

