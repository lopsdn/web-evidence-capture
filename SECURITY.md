# Security

Do not commit raw evidence, cookie values, credentials, tokens, private keys, or raw request bodies unless they have been intentionally reviewed and approved for the repository context.

Runtime case outputs are ignored by default. GitHub Actions artifacts remain private to repository users with access.

If you find a security issue in this tool, report it privately to the repository owner. Do not disclose sensitive capture artifacts publicly.

## Sensitive Data Handling

- Cookie summaries record names, domains, flags, and value lengths by default.
- Raw cookie values are not written by the privacy inspector by default.
- Raw request bodies are not written by the privacy inspector by default.
- Validation scans text outputs for common secret-like patterns before marking a package validated.

