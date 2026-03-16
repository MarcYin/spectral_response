from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rsrf.io import artifact_file_count, artifact_sha256, artifact_size_bytes


class ArtifactIoTests(unittest.TestCase):
    def test_directory_artifact_helpers_are_stable(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "a.txt").write_text("alpha\n", encoding="utf-8")
            nested = root / "nested"
            nested.mkdir()
            (nested / "b.txt").write_text("beta\n", encoding="utf-8")

            first_digest = artifact_sha256(root)
            second_digest = artifact_sha256(root)

            self.assertEqual(first_digest, second_digest)
            self.assertEqual(artifact_file_count(root), 2)
            self.assertEqual(
                artifact_size_bytes(root),
                (root / "a.txt").stat().st_size + (nested / "b.txt").stat().st_size,
            )


if __name__ == "__main__":
    unittest.main()
