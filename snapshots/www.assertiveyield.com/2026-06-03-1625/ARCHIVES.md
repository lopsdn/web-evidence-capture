# Snapshot Archives

This file explains where the generated ZIP archives are stored.

The expanded snapshot directory is committed to Git. Large ZIP archives may be stored outside the Git tree because GitHub rejects individual Git files above 100 MB.

| Archive | Size bytes | SHA-256 | Committed in this snapshot | External path |
| --- | ---: | --- | --- | --- |
| `www.assertiveyield.com-2026-06-03-1625.zip` | 1484524186 | `e659b947bc436ef1939148a6f4de041589661ab6f992b8be0c19774f959a5966` | `no` | `snapshot-archives/www.assertiveyield.com/2026-06-03-1625/www.assertiveyield.com-2026-06-03-1625.zip` |
| `www.assertiveyield.com-2026-06-03-1625-website-html.zip` | 424550106 | `30c38de751059a28e58aec899e7f35da9c5e81cd618a732a35b0a3a32fde1cf7` | `no` | `snapshot-archives/www.assertiveyield.com/2026-06-03-1625/www.assertiveyield.com-2026-06-03-1625-website-html.zip` |

If an external path is listed, the workflow uploads that file from `snapshot-archives/` as a workflow artifact and, when configured, as a release asset. Use the SHA-256 values above to verify downloaded archives.
