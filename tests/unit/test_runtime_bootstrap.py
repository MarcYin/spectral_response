from __future__ import annotations

import shutil
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rsrf.registry import (
    RUNTIME_READY_MARKER_FILENAME,
    _runtime_release_archive_candidates,
    _runtime_release_root,
)


class RuntimeBootstrapTests(unittest.TestCase):
    def test_archive_candidates_fall_back_to_main_snapshot(self) -> None:
        candidates = _runtime_release_archive_candidates("0.3.1")
        self.assertEqual(len(candidates), 3)
        self.assertTrue(candidates[0].endswith("/releases/download/v0.3.1/rsrf-root-v0.3.1.tar.gz"))
        self.assertTrue(candidates[1].endswith("/archive/refs/tags/v0.3.1.tar.gz"))
        self.assertTrue(candidates[2].endswith("/archive/refs/heads/main.tar.gz"))

    def _write_runtime_archive(self, archive_path: Path, *, top_level_dir: str | None) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            bundle_parent = Path(tmpdir)
            bundle_root = bundle_parent / "bundle" if top_level_dir is None else bundle_parent / top_level_dir

            (bundle_root / "data" / "registry").mkdir(parents=True, exist_ok=True)
            (bundle_root / "data" / "registry" / "sensors.parquet").write_text("placeholder", encoding="utf-8")
            (bundle_root / "sources" / "manifests" / "official").mkdir(parents=True, exist_ok=True)
            (bundle_root / "pyproject.toml").write_text('[project]\nversion = "0.3.0"\n', encoding="utf-8")

            with tarfile.open(archive_path, "w:gz") as archive:
                if top_level_dir is None:
                    for child in bundle_root.iterdir():
                        archive.add(child, arcname=child.name)
                else:
                    archive.add(bundle_root, arcname=bundle_root.name)

    def test_runtime_release_root_extracts_source_archive_layout(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            archive_path = Path(tmpdir) / "source-archive.tar.gz"
            cache_base = Path(tmpdir) / "cache"
            self._write_runtime_archive(archive_path, top_level_dir="spectral_response-0.3.0")

            def fake_download(version: str, destination: Path) -> str:
                self.assertEqual(version, "0.3.0")
                shutil.copyfile(archive_path, destination)
                return "https://example.invalid/source-archive.tar.gz"

            with (
                patch("rsrf.registry._installed_package_version", return_value="0.3.0"),
                patch("rsrf.registry._cache_base_directory", return_value=cache_base),
                patch("rsrf.registry._download_runtime_release_archive", side_effect=fake_download),
            ):
                runtime_root = _runtime_release_root()

            expected_root = cache_base / "rsrf" / "releases" / "0.3.0"
            self.assertEqual(runtime_root, expected_root)
            self.assertTrue((runtime_root / "data" / "registry" / "sensors.parquet").exists())
            self.assertTrue((runtime_root / RUNTIME_READY_MARKER_FILENAME).exists())

            with (
                patch("rsrf.registry._download_runtime_release_archive", side_effect=AssertionError("cache miss")),
                patch("rsrf.registry._installed_package_version", return_value="0.3.0"),
                patch("rsrf.registry._cache_base_directory", return_value=cache_base),
            ):
                cached_root = _runtime_release_root()
            self.assertEqual(cached_root, expected_root)

    def test_runtime_release_root_extracts_direct_bundle_layout(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            archive_path = Path(tmpdir) / "direct-bundle.tar.gz"
            cache_base = Path(tmpdir) / "cache"
            self._write_runtime_archive(archive_path, top_level_dir=None)

            def fake_download(version: str, destination: Path) -> str:
                self.assertEqual(version, "0.3.0")
                shutil.copyfile(archive_path, destination)
                return "https://example.invalid/direct-bundle.tar.gz"

            with (
                patch("rsrf.registry._installed_package_version", return_value="0.3.0"),
                patch("rsrf.registry._cache_base_directory", return_value=cache_base),
                patch("rsrf.registry._download_runtime_release_archive", side_effect=fake_download),
            ):
                runtime_root = _runtime_release_root()

            self.assertTrue((runtime_root / "data" / "registry" / "sensors.parquet").exists())
            self.assertTrue((runtime_root / RUNTIME_READY_MARKER_FILENAME).exists())


if __name__ == "__main__":
    unittest.main()
