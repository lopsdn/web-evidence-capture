# Private Output Model

V1 is private-output only for local work. Local runtime evidence under `cases/` is not committed by default.

GitHub Actions captures are durable by design: the workflow uploads a private artifact and commits a copy under:

```text
snapshots/<site>/<YYYY-MM-DD-HHMM>/
```

The committed snapshot is intended to remain available after the GitHub Actions run and its native logs expire. The workflow commits the same snapshot path progressively after each major job, so a reviewer can inspect partial output before the final job completes.

Each snapshot should include:

- `START-HERE.md` with simple opening and download instructions.
- README files explaining the folder contents and forensic value.
- The expanded evidence package.
- A ZIP archive of the snapshot directory, unless the archive is too large for GitHub's per-file Git limit.
- A smaller website HTML ZIP for local browsing, unless the archive is too large for GitHub's per-file Git limit.
- Reports, manifests, validation results, hashes, and structured logs.
- GitHub Actions run/job metadata and workflow logs when GitHub exposes them during the final job.
- Raw public-runner browser observations such as cookies, storage state, request/response headers, query values, request bodies, console events, and page errors.

For ordinary review, open `SNAPSHOT-STATUS.md` first if the workflow is still running. Then open `START-HERE.md` and `report/report.md` when they exist. To navigate preserved HTML locally after the final job, download `<site>-<run>-website-html.zip`, unzip it, and open `index.html`. From there, open the rendered mirror, the offline site map, the static mirror, or SingleFile exports. Use `site-map.html` when menus, dropdowns, or scripted controls do not work offline.

If a ZIP is too large to commit, open `ARCHIVES.md`. The snapshot records SHA-256 hashes and external paths under `manifest/snapshot-archives.json`, and the workflow publishes the large ZIPs as workflow artifacts and release assets instead of Git files.

Future versions may add explicit redacted publication modes, but they are intentionally not included in v1.
