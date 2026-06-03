# Limitations

This tool cannot prove that a website has no other public content. It captures the public content reachable through the configured scope during the capture window.

Known limitations:

- Dynamic applications can render differently across browser sessions.
- WACZ validation can pass even when page index detection is incomplete; this is reported separately.
- Static mirrors are review aids, not replacements for WARC/WACZ.
- Browser screenshots and PDFs depend on viewport, browser version, fonts, and network timing.
- Privacy summaries avoid raw values by default and may omit details that require specialized forensic tooling.

