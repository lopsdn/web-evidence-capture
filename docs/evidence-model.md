# Evidence Model

Each run creates a deterministic folder under `cases/<case_slug>/runs/<YYYY-MM-DD-HHMM>/`.

The main evidence groups are:

- `manifest/`: structured JSON records for inventory, capture, rendering, WACZ, validation, and report generation.
- `artifacts/`: private raw preservation outputs such as mirror files, WARC/WACZ, screenshots, PDFs, downloads, and SingleFile HTML.
- `logs/`: structured step logs.
- `hashes/`: SHA-256 hash lists.
- `validation/`: validation JSON and reviewer-facing validation records.
- `report/`: generated Markdown reports.

Hash manifests exclude their own generated files to avoid self-referential hash instability.

