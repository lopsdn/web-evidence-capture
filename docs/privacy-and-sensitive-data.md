# Privacy And Sensitive Data

The tool minimizes sensitive capture in logs and summaries:

- cookie values are summarized by value length;
- request bodies are not written by default;
- query parameter names may be recorded, but values are avoided in privacy summaries;
- validation scans text outputs for common secret-like patterns.

Private repository visibility does not eliminate the need for evidence review. Raw artifacts can still contain personal data, tracking identifiers, copyrighted materials, or third-party content.

