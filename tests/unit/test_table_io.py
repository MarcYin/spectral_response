from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rsrf.io import parquet_support_available, read_parquet_table, write_parquet_table
from rsrf.io import read_json
from rsrf.manifests import manifest_path
from rsrf.registry import manifest_registry_rows, registry_table_columns
from rsrf.validate import parse_manifest_dict


class TableIoTests(unittest.TestCase):
    def test_parquet_write_path_matches_environment_capabilities(self) -> None:
        payload = read_json(manifest_path(ROOT, "rsrf_source_manifest_sentinel2c_v2.json"))
        manifest = parse_manifest_dict(payload)
        rows = manifest_registry_rows(manifest)["sensors"]

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sensors.parquet"
            if parquet_support_available():
                write_parquet_table(
                    path,
                    rows,
                    columns=registry_table_columns("sensors"),
                )
                frame = read_parquet_table(path)
                self.assertEqual(list(frame.columns), list(registry_table_columns("sensors")))
                self.assertEqual(frame.iloc[0]["sensor_unit_id"], "sentinel-2c_msi")
            else:
                with self.assertRaisesRegex(RuntimeError, "Parquet support requires"):
                    write_parquet_table(
                        path,
                        rows,
                        columns=registry_table_columns("sensors"),
                    )


if __name__ == "__main__":
    unittest.main()
