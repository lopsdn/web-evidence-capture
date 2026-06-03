# Private Output Model

V1 is private-output only for local work. Local runtime evidence under `cases/` is not committed by default.

GitHub Actions captures are durable by design: the workflow uploads a private artifact and commits a copy under:

```text
snapshots/<site>/<YYYY-MM-DD-HHMM>/
```

The committed snapshot is intended to remain available after the GitHub Actions run and its native logs expire.

Each snapshot should include:

- `START-HERE.md` with simple opening and download instructions.
- README files explaining the folder contents and forensic value.
- The expanded evidence package.
- A ZIP archive of the snapshot directory.
- A smaller website HTML ZIP for local browsing.
- Reports, manifests, validation results, hashes, and structured logs.
- GitHub Actions run/job metadata and workflow logs when GitHub exposes them during the final job.
- Raw public-runner browser observations such as cookies, storage state, request/response headers, query values, request bodies, console events, and page errors.

For ordinary review, open `START-HERE.md` first, then `report/report.md`. To navigate preserved HTML locally, download `<site>-<run>-website-html.zip`, unzip it, and open `open-rendered-mirror.html`. If the rendered mirror is unavailable or not useful, open `open-static-mirror.html`. For self-contained individual page exports, open `singlefile-index.html` when available.

Future versions may add explicit redacted publication modes, but they are intentionally not included in v1.
