from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rsrf.io import write_parquet_table
from rsrf.manifests import PLANNING_MANIFEST_DIRNAME, manifest_path
from rsrf.planning import list_planned_sensors, load_planned_sensor_catalog, register_planned_sensor_catalog
from rsrf.registry import read_registry_table, registry_table_columns, registry_table_path


class PlanningTests(unittest.TestCase):
    def test_load_planned_sensor_catalog_returns_expected_entries(self) -> None:
        catalog = load_planned_sensor_catalog(ROOT)
        entries = catalog["entries"]

        self.assertEqual(catalog["bucket"], "P2")
        self.assertEqual(entries, [])

    def test_list_planned_sensors_returns_json_friendly_rows(self) -> None:
        rows = list_planned_sensors(ROOT)

        self.assertEqual(rows, [])

    def test_register_planned_sensor_catalog_writes_sensor_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            written = register_planned_sensor_catalog(
                tmp_root,
                catalog_path=manifest_path(
                    ROOT,
                    "p2_planned_optical_sensors.json",
                    manifest_group=PLANNING_MANIFEST_DIRNAME,
                ),
            )
        self.assertIsNone(written)
        with self.assertRaises(FileNotFoundError):
            read_registry_table(tmp_root, "sensors")

    def test_register_planned_sensor_catalog_removes_stale_planned_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            sensors_path = registry_table_path(tmp_root, "sensors")
            write_parquet_table(
                sensors_path,
                [
                    {
                        "sensor_unit_id": "sentinel-2c_msi",
                        "representation_variant": "band_average",
                        "content_kind": "sampled_curve",
                        "status": "registered",
                    },
                    {
                        "sensor_unit_id": "prisma_hsi",
                        "representation_variant": "metadata_band_spec",
                        "content_kind": "band_spec",
                        "status": "planned",
                    },
                ],
                columns=registry_table_columns("sensors"),
            )

            written = register_planned_sensor_catalog(
                tmp_root,
                catalog_path=manifest_path(
                    ROOT,
                    "p2_planned_optical_sensors.json",
                    manifest_group=PLANNING_MANIFEST_DIRNAME,
                ),
            )
            sensors = read_registry_table(tmp_root, "sensors")

        self.assertIsNotNone(written)
        self.assertEqual(set(sensors["sensor_unit_id"].tolist()), {"sentinel-2c_msi"})
        self.assertTrue((sensors["status"] != "planned").all())


if __name__ == "__main__":
    unittest.main()
