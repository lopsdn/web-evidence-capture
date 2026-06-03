# Cases

Local case run outputs are private by default and ignored by Git.

Expected runtime layout:

```text
cases/<case_slug>/runs/<YYYY-MM-DD-HHMM>/
  artifacts/
  hashes/
  logs/
  manifest/
  report/
  validation/
```

Raw evidence such as screenshots, PDFs, WARC/WACZ files, mirrors, cookies, and network logs should not be committed unless intentionally reviewed and approved.

GitHub Actions captures are intentionally committed under:

```text
snapshots/<site>/<YYYY-MM-DD-HHMM>/
```

Open the snapshot's `START-HERE.md` first, then `report/report.md`. The snapshot should include expanded evidence, a complete ZIP archive, a smaller website HTML ZIP for local browsing, reports, manifests, validation results, hashes, tool logs, GitHub Actions metadata/logs, and preserved public-runner browser evidence.
