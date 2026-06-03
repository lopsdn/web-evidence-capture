# Snapshot Archives

This file explains where the generated ZIP archives are stored.

The expanded snapshot directory is committed to Git. Large ZIP archives may be stored outside the Git tree because GitHub rejects individual Git files above 100 MB.

| Archive | Size bytes | SHA-256 | Committed in this snapshot | External path |
| --- | ---: | --- | --- | --- |
| `www.assertiveyield.com-2026-06-03-1625.zip` | 1484168810 | `958de834e8ca5ebe815d9f4762ff911abc1d0912eefd0a0221155915fcfa396f` | `no` | `snapshot-archives/www.assertiveyield.com/2026-06-03-1625/www.assertiveyield.com-2026-06-03-1625.zip` |
| `www.assertiveyield.com-2026-06-03-1625-website-html.zip` | 424372284 | `d71de001e5c1baaa54d21172d03ef977e28fe46ae5eb933f2ca689029324355c` | `no` | `snapshot-archives/www.assertiveyield.com/2026-06-03-1625/www.assertiveyield.com-2026-06-03-1625-website-html.zip` |

If an external path is listed, the workflow uploads that file from `snapshot-archives/` as a workflow artifact and, when configured, as a release asset. Use the SHA-256 values above to verify downloaded archives.
