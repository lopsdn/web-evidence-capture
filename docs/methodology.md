# Methodology

The standard capture process is staged:

1. Define target URL, allowed domains, page limit, cookie choice, and output path.
2. Capture robots and sitemap control files.
3. Build a public URL inventory from sitemaps and public links.
4. Capture public pages with polite GET requests into a static mirror and WARC.
5. Render selected pages to screenshots and PDFs.
6. Inspect privacy behavior through summary-only browser network and cookie metadata.
7. Optionally export SingleFile HTML when the CLI is available.
8. Package WARC into WACZ and validate it.
9. Generate hashes, validation evidence, and human-readable reports.

The methodology forbids authentication, account creation, and form submission.

