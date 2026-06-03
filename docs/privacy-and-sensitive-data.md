# Public Runner Browser Evidence And Sensitive Data

V1 is designed for private repository use. Browser/network inspection may preserve public-runner observations in detail, including:

- target-site cookie names and values;
- browser storage state;
- request and response headers;
- query names and values;
- request bodies observed during public browsing;
- console events and page errors.

This detail can have forensic value because it records what the public GitHub-hosted runner observed while loading the site. It also means snapshots can contain personal data, tracking identifiers, copyrighted content, or third-party content.

Repository secrets and platform tokens should not be printed or committed. Private repository visibility does not eliminate the need for evidence review before sharing any output outside the repository.
