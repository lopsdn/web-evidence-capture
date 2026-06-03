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

Workflow logs are structured and should not expose secrets, cookie values, token values, or raw request bodies.

