from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rsrf.manifests import resolve_manifest_path


class ResolveManifestPathTests(unittest.TestCase):
    def test_existing_library_manifest_resolves(self) -> None:
        path = resolve_manifest_path(
            "rsrf_source_manifest_sentinel2c_v2.json",
            root=ROOT,
        )
        self.assertTrue(path.exists())
        self.assertTrue(path.name.endswith(".json"))

    def test_missing_manifest_raises_file_not_found(self) -> None:
        with self.assertRaises(FileNotFoundError):
            resolve_manifest_path("nonexistent_manifest.json", root=ROOT)

    def test_relative_path_outside_repo_raises_value_error(self) -> None:
        # A relative path that resolves (via cwd) to somewhere outside the repo
        # should be rejected by the containment check.
        import os
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest = Path(tmpdir) / "sneaky.json"
            manifest.write_text("{}")
            saved_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                with self.assertRaises(ValueError):
                    resolve_manifest_path("sneaky.json", root=ROOT)
            finally:
                os.chdir(saved_cwd)


if __name__ == "__main__":
    unittest.main()
