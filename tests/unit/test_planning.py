from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rsrf.planning import list_planned_sensors, load_planned_sensor_catalog, register_planned_sensor_catalog
from rsrf.registry import read_registry_table


class PlanningTests(unittest.TestCase):
    def test_load_planned_sensor_catalog_returns_expected_entries(self) -> None:
        catalog = load_planned_sensor_catalog(ROOT)
        entries = catalog["entries"]

        self.assertEqual(catalog["bucket"], "P2")
        self.assertEqual(len(entries), 1)
        sensor_ids = {entry.sensor_unit_id for entry in entries}
        self.assertIn("prisma_hsi", sensor_ids)
        self.assertNotIn("pleiades_msi", sensor_ids)
        self.assertNotIn("formosat-5_rsi", sensor_ids)

    def test_list_planned_sensors_returns_json_friendly_rows(self) -> None:
        rows = list_planned_sensors(ROOT)

        self.assertEqual(len(rows), 1)
        row = next(row for row in rows if row["sensor_unit_id"] == "prisma_hsi")
        self.assertEqual(row["content_kind"], "band_spec")
        self.assertEqual(row["status"], "planned")

    def test_register_planned_sensor_catalog_writes_sensor_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            written = register_planned_sensor_catalog(
                tmp_root,
                catalog_path=ROOT / "sources" / "manifests" / "p2_planned_optical_sensors.json",
            )
            sensors = read_registry_table(tmp_root, "sensors")

        self.assertIsNotNone(written)
        self.assertEqual(len(sensors), 1)
        sensor_ids = set(sensors["sensor_unit_id"].tolist())
        self.assertEqual(sensor_ids, {"prisma_hsi"})
        planned = sensors[sensors["status"] == "planned"]
        self.assertEqual(len(planned), 1)


if __name__ == "__main__":
    unittest.main()
