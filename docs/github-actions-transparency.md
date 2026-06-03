# GitHub Actions Transparency

When the workflow captures a website, it does so from a GitHub-hosted runner. Reports must disclose this because captured content can differ by:

- runner geography;
- CDN routing;
- browser version;
- current date and time;
- cookie state;
- A/B testing;
- third-party service availability;
- network behavior.

Workflow logs are structured and should not expose repository secrets or GitHub token values. Target-site cookies, public-runner browser storage, request/response headers, query values, and request bodies may be captured as evidence because they describe the public browsing session created by the workflow.

After each major job, the workflow commits the current snapshot state under `snapshots/<site>/<run>/`. Open `SNAPSHOT-STATUS.md` to see which stage has completed. This progressive commit model is intended for live review during long captures.

The workflow persists GitHub Actions run/job metadata and text logs into the snapshot under:

```text
logs/github-actions/
```

This is necessary because native GitHub Actions logs are retained only for a limited period. The final job may not be able to include every line from its own currently running step, but it records the workflow/job metadata and available logs before committing the snapshot.

The final job also writes a simple `START-HERE.md` guide into the snapshot and creates two archives:

- `<site>-<run>.zip`: the complete evidence package.
- `<site>-<run>-website-html.zip`: a smaller package for local HTML browsing.
