from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rsrf.registry import REGISTRY_TABLES, RSRF_ROOT_ENV_VAR, build_repo_layout, registry_table_path


class RegistryLayoutTests(unittest.TestCase):
    def test_repo_layout_points_to_expected_directories(self) -> None:
        layout = build_repo_layout(ROOT)
        self.assertEqual(layout.package_root, ROOT / "src" / "rsrf")
        self.assertEqual(layout.source_manifests_root, ROOT / "sources" / "manifests")
        self.assertEqual(
            layout.official_source_manifests_root,
            ROOT / "sources" / "manifests" / "official",
        )
        self.assertEqual(
            layout.planning_source_manifests_root,
            ROOT / "sources" / "manifests" / "planning",
        )
        self.assertEqual(
            layout.template_source_manifests_root,
            ROOT / "sources" / "manifests" / "templates",
        )
        self.assertEqual(layout.registry_root, ROOT / "data" / "registry")

    def test_registry_paths_follow_table_names(self) -> None:
        for table_name in REGISTRY_TABLES:
            self.assertEqual(
                registry_table_path(ROOT, table_name),
                ROOT / "data" / "registry" / f"{table_name}.parquet",
            )

    def test_build_repo_layout_honors_rsrf_root_environment_variable(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            expected_root = Path(tmpdir).resolve()
            with patch.dict(os.environ, {RSRF_ROOT_ENV_VAR: str(expected_root)}, clear=False):
                layout = build_repo_layout()

        self.assertEqual(layout.root, expected_root)


if __name__ == "__main__":
    unittest.main()
