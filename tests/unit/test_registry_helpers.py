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

from rsrf.registry import (
    REGISTRY_TABLES,
    build_repo_layout,
    canonical_variant_dir,
    discover_repo_root,
    ensure_repo_layout,
    realized_variant_dir,
    registry_primary_key,
    registry_table_columns,
    registry_table_path,
    representation_variant_dir,
    sensor_row_from_manifest,
    source_row_from_manifest,
)


class DiscoverRepoRootTests(unittest.TestCase):
    def test_discovers_from_explicit_start(self) -> None:
        root = discover_repo_root(ROOT)
        self.assertTrue((root / "pyproject.toml").exists())

    def test_discovers_from_env_var(self) -> None:
        original = os.environ.get("RSRF_ROOT")
        try:
            os.environ["RSRF_ROOT"] = str(ROOT)
            root = discover_repo_root()
            self.assertEqual(root, ROOT.resolve())
        finally:
            if original is None:
                os.environ.pop("RSRF_ROOT", None)
            else:
                os.environ["RSRF_ROOT"] = original

    def test_invalid_env_var_raises(self) -> None:
        original = os.environ.get("RSRF_ROOT")
        try:
            os.environ["RSRF_ROOT"] = "/nonexistent/path/rsrf"
            with self.assertRaises(FileNotFoundError):
                discover_repo_root()
        finally:
            if original is None:
                os.environ.pop("RSRF_ROOT", None)
            else:
                os.environ["RSRF_ROOT"] = original


class EnsureRepoLayoutTests(unittest.TestCase):
    def test_creates_directories(self) -> None:
        layout = ensure_repo_layout(ROOT)
        self.assertTrue(layout.registry_root.is_dir())
        self.assertTrue(layout.canonical_root.is_dir())


class RegistryTablePathTests(unittest.TestCase):
    def test_known_tables(self) -> None:
        for table_name in REGISTRY_TABLES:
            path = registry_table_path(ROOT, table_name)
            self.assertTrue(path.name.endswith(".parquet"))

    def test_unknown_table_raises(self) -> None:
        with self.assertRaises(ValueError):
            registry_table_path(ROOT, "nonexistent")


class RegistryTableColumnsTests(unittest.TestCase):
    def test_known_tables_return_tuples(self) -> None:
        for table_name in REGISTRY_TABLES:
            cols = registry_table_columns(table_name)
            self.assertIsInstance(cols, tuple)
            self.assertGreater(len(cols), 0)

    def test_unknown_table_raises(self) -> None:
        with self.assertRaises(ValueError):
            registry_table_columns("nonexistent")


class RegistryPrimaryKeyTests(unittest.TestCase):
    def test_known_tables(self) -> None:
        for table_name in REGISTRY_TABLES:
            pk = registry_primary_key(table_name)
            self.assertIsInstance(pk, tuple)
            self.assertGreater(len(pk), 0)

    def test_unknown_table_raises(self) -> None:
        with self.assertRaises(ValueError):
            registry_primary_key("nonexistent")


class VariantDirTests(unittest.TestCase):
    def test_canonical_variant_dir(self) -> None:
        d = canonical_variant_dir(ROOT, "sampled_curve", "test_sensor", "variant_a")
        self.assertIn("sampled_curve", str(d))
        self.assertIn("test_sensor", str(d))

    def test_realized_variant_dir(self) -> None:
        d = realized_variant_dir(ROOT, "test_sensor", "variant_a")
        self.assertIn("realized", str(d))

    def test_representation_variant_dir_canonical(self) -> None:
        d = representation_variant_dir(
            ROOT,
            sensor_unit_id="s",
            representation_variant="v",
            content_kind="sampled_curve",
            realization_kind="none",
        )
        self.assertIn("canonical", str(d))

    def test_representation_variant_dir_realized(self) -> None:
        d = representation_variant_dir(
            ROOT,
            sensor_unit_id="s",
            representation_variant="v",
            content_kind="sampled_curve",
            realization_kind="approximate_parametric",
        )
        self.assertIn("realized", str(d))


if __name__ == "__main__":
    unittest.main()
