# GitHub Actions Run Log Summary

This folder preserves workflow metadata and text logs inside the committed snapshot because native workflow logs may expire or be deleted.

Run URL: https://github.com/lopsdn/web-evidence-capture/actions/runs/26898253212
Run status: `in_progress`
Run conclusion at capture time: ``
Event: `workflow_dispatch`
Head branch: `main`
Head SHA: `b809f1bf953a88babb764e2a58818905d301fce7`
Created at: `2026-06-03T16:24:58Z`
Updated at: `2026-06-03T17:50:19Z`

## Jobs

| Job | Status | Conclusion | Started | Completed | Steps | Log lines |
| --- | --- | --- | --- | --- | ---: | ---: |
| scope | `completed` | `success` | `2026-06-03T16:25:07Z` | `2026-06-03T16:26:01Z` | 12 | 0 |
| inventory | `completed` | `success` | `2026-06-03T16:26:04Z` | `2026-06-03T16:30:02Z` | 12 | 0 |
| capture | `completed` | `success` | `2026-06-03T16:30:06Z` | `2026-06-03T16:33:39Z` | 12 | 0 |
| render | `completed` | `success` | `2026-06-03T16:33:42Z` | `2026-06-03T16:51:23Z` | 12 | 0 |
| privacy_inspection | `completed` | `success` | `2026-06-03T16:51:26Z` | `2026-06-03T17:04:46Z` | 12 | 0 |
| singlefile | `completed` | `success` | `2026-06-03T17:04:49Z` | `2026-06-03T17:38:04Z` | 14 | 0 |
| package_wacz | `completed` | `success` | `2026-06-03T17:38:07Z` | `2026-06-03T17:41:05Z` | 12 | 0 |
| hash_manifest | `completed` | `success` | `2026-06-03T17:41:09Z` | `2026-06-03T17:44:50Z` | 12 | 0 |
| validate | `completed` | `success` | `2026-06-03T17:44:53Z` | `2026-06-03T17:47:21Z` | 12 | 0 |
| generate_report | `completed` | `success` | `2026-06-03T17:47:24Z` | `2026-06-03T17:50:15Z` | 12 | 0 |
| upload_private_artifacts | `in_progress` | `` | `2026-06-03T17:50:18Z` | `0001-01-01T00:00:00Z` | 13 | 0 |

## Files

- `run-metadata.json`: workflow run metadata.
- `jobs.json`: job and step metadata returned by the workflow API.
- `run.log`: raw text log returned by the workflow API.
- `failed.log`: failed-step log excerpt returned by the workflow API, when any.
- `jobs/*.log`: raw log lines split by job name.
- `job-log-index.json`: machine-readable index of split job logs.

The final snapshot commit step may not include its own last lines because the log is captured while the job is still running.
