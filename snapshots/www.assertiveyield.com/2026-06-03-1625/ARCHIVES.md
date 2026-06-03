# Snapshot Archives

This file explains where the generated ZIP archives are stored.

The expanded snapshot directory is committed to Git. Large ZIP archives may be stored outside the Git tree because GitHub rejects individual Git files above 100 MB.

| Archive | Size bytes | SHA-256 | Committed in this snapshot | External path |
| --- | ---: | --- | --- | --- |
| `www.assertiveyield.com-2026-06-03-1625.zip` | 1484154405 | `e356189345caf4a6e1ef820dd4dff595b8ee4ced9dd4f15d4902cc24e85f9f36` | `no` | `snapshot-archives/www.assertiveyield.com/2026-06-03-1625/www.assertiveyield.com-2026-06-03-1625.zip` |
| `www.assertiveyield.com-2026-06-03-1625-website-html.zip` | 424365657 | `6ef554bc20352c3def942f6221f55ca2ef42c67f4d34e74105a0172edbd4c496` | `no` | `snapshot-archives/www.assertiveyield.com/2026-06-03-1625/www.assertiveyield.com-2026-06-03-1625-website-html.zip` |

If an external path is listed, the workflow uploads that file from `snapshot-archives/` as a workflow artifact and, when configured, as a release asset. Use the SHA-256 values above to verify downloaded archives.
