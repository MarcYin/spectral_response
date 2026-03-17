from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rsrf.manifests import (
    OFFICIAL_MANIFEST_DIRNAME,
    PLANNING_MANIFEST_DIRNAME,
    TEMPLATE_MANIFEST_DIRNAME,
    iter_source_manifest_paths,
    manifest_path,
    resolve_manifest_path,
)


class ManifestLibraryTests(unittest.TestCase):
    def test_manifest_path_points_to_grouped_manifest_directories(self) -> None:
        self.assertEqual(
            manifest_path(
                ROOT,
                "rsrf_source_manifest_sentinel2c_v2.json",
                manifest_group=OFFICIAL_MANIFEST_DIRNAME,
            ),
            ROOT / "sources" / "manifests" / "official" / "rsrf_source_manifest_sentinel2c_v2.json",
        )
        self.assertEqual(
            manifest_path(
                ROOT,
                "p2_planned_optical_sensors.json",
                manifest_group=PLANNING_MANIFEST_DIRNAME,
            ),
            ROOT / "sources" / "manifests" / "planning" / "p2_planned_optical_sensors.json",
        )
        self.assertEqual(
            manifest_path(
                ROOT,
                "rsrf_source_manifest_template_v2.json",
                manifest_group=TEMPLATE_MANIFEST_DIRNAME,
            ),
            ROOT / "sources" / "manifests" / "templates" / "rsrf_source_manifest_template_v2.json",
        )

    def test_resolve_manifest_path_accepts_manifest_library_filenames(self) -> None:
        resolved = resolve_manifest_path("rsrf_source_manifest_sentinel2c_v2.json", root=ROOT)
        self.assertEqual(
            resolved,
            ROOT / "sources" / "manifests" / "official" / "rsrf_source_manifest_sentinel2c_v2.json",
        )

    def test_resolve_manifest_path_uses_explicit_root_outside_repo_cwd(self) -> None:
        previous_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                os.chdir(tmpdir)
                resolved = resolve_manifest_path(
                    "rsrf_source_manifest_sentinel2c_v2.json",
                    root=ROOT,
                )
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(
            resolved,
            ROOT / "sources" / "manifests" / "official" / "rsrf_source_manifest_sentinel2c_v2.json",
        )

    def test_iter_source_manifest_paths_lists_official_manifests(self) -> None:
        paths = iter_source_manifest_paths(ROOT)
        self.assertGreater(len(paths), 10)
        self.assertNotIn("rsrf_source_manifest_template_v2.json", {path.name for path in paths})

    def test_iter_source_manifest_paths_can_include_templates_and_planning(self) -> None:
        paths = iter_source_manifest_paths(ROOT, include_templates=True, include_planning=True)
        names = {path.name for path in paths}
        self.assertIn("rsrf_source_manifest_template_v2.json", names)
        self.assertIn("p2_planned_optical_sensors.json", names)


if __name__ == "__main__":
    unittest.main()
