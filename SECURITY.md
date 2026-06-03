# Security

Do not commit raw evidence, credentials, tokens, private keys, or non-public material unless they have been intentionally reviewed and approved for the repository context.

Runtime case outputs are ignored by default. GitHub Actions artifacts and committed snapshots remain private to repository users with access.

If you find a security issue in this tool, report it privately to the repository owner. Do not disclose sensitive capture artifacts publicly.

## Sensitive Data Handling

- Private workflow captures may preserve target-site cookie values, browser storage, headers, query values, and request bodies observed during the public runner session.
- Repository secrets and platform tokens should not be printed or committed.
- Do not add authentication secrets or private account material to capture configuration.
- Validation scans text outputs for common secret-like patterns before marking a package validated.
