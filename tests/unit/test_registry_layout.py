from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rsrf.registry import REGISTRY_TABLES, build_repo_layout, registry_table_path


class RegistryLayoutTests(unittest.TestCase):
    def test_repo_layout_points_to_expected_directories(self) -> None:
        layout = build_repo_layout(ROOT)
        self.assertEqual(layout.package_root, ROOT / "src" / "rsrf")
        self.assertEqual(layout.source_manifests_root, ROOT / "sources" / "manifests")
        self.assertEqual(layout.registry_root, ROOT / "data" / "registry")

    def test_registry_paths_follow_table_names(self) -> None:
        for table_name in REGISTRY_TABLES:
            self.assertEqual(
                registry_table_path(ROOT, table_name),
                ROOT / "data" / "registry" / f"{table_name}.parquet",
            )


if __name__ == "__main__":
    unittest.main()
