# Snapshot Archives

This file explains where the generated ZIP archives are stored.

The expanded snapshot directory is committed to Git. Large ZIP archives may be stored outside the Git tree because GitHub rejects individual Git files above 100 MB.

| Archive | Size bytes | SHA-256 | Committed in this snapshot | External path |
| --- | ---: | --- | --- | --- |
| `www.assertiveyield.com-2026-06-03-1625.zip` | 1484077866 | `375385addee94d359ef5888dabe19aa72a433902fce0a15f9f9df76a2b9ca45c` | `no` | `snapshot-archives/www.assertiveyield.com/2026-06-03-1625/www.assertiveyield.com-2026-06-03-1625.zip` |
| `www.assertiveyield.com-2026-06-03-1625-website-html.zip` | 424326838 | `9682a3a71328c08b6a96efaf25d93f1dc0bc22bd4bd6f3809a49266cd53c58c0` | `no` | `snapshot-archives/www.assertiveyield.com/2026-06-03-1625/www.assertiveyield.com-2026-06-03-1625-website-html.zip` |

If an external path is listed, the workflow uploads that file from `snapshot-archives/` as a workflow artifact and, when configured, as a release asset. Use the SHA-256 values above to verify downloaded archives.
