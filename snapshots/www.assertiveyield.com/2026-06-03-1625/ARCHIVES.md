# Snapshot Archives

This file explains where the generated ZIP archives are stored.

The expanded snapshot directory is committed to Git. Large ZIP archives may be stored outside the Git tree because GitHub rejects individual Git files above 100 MB.

| Archive | Size bytes | SHA-256 | Committed in this snapshot | External path |
| --- | ---: | --- | --- | --- |
| `www.assertiveyield.com-2026-06-03-1625.zip` | 1484078057 | `ba110128229937d2c9a885b31d0399354740685ddf029670f1529f33800b527a` | `no` | `snapshot-archives/www.assertiveyield.com/2026-06-03-1625/www.assertiveyield.com-2026-06-03-1625.zip` |
| `www.assertiveyield.com-2026-06-03-1625-website-html.zip` | 424326838 | `1a7bd1975120f5a8be746af9808eacc20ef8df07d54e341fdf21bf1b19cdfa2b` | `no` | `snapshot-archives/www.assertiveyield.com/2026-06-03-1625/www.assertiveyield.com-2026-06-03-1625-website-html.zip` |

If an external path is listed, the workflow uploads that file from `snapshot-archives/` as a workflow artifact and, when configured, as a release asset. Use the SHA-256 values above to verify downloaded archives.
