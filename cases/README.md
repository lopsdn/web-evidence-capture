# Cases

Case run outputs are private by default and ignored by Git.

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

