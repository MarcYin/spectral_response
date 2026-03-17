from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rsrf.io import parquet_support_available, read_json
from rsrf.manifests import manifest_path
from rsrf.registry import read_registry_table, register_manifest
from rsrf.validate import parse_manifest_dict


class RegistryPersistenceTests(unittest.TestCase):
    def test_register_manifest_respects_parquet_support(self) -> None:
        payload = read_json(manifest_path(ROOT, "rsrf_source_manifest_sentinel2c_v2.json"))
        manifest = parse_manifest_dict(payload)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            (tmp_root / "data" / "registry").mkdir(parents=True, exist_ok=True)
            if parquet_support_available():
                written = register_manifest(tmp_root, manifest)
                self.assertIn("sensors", written)
                frame = read_registry_table(tmp_root, "sensors")
                self.assertEqual(frame.iloc[0]["sensor_unit_id"], "sentinel-2c_msi")
            else:
                with self.assertRaisesRegex(RuntimeError, "Parquet support requires"):
                    register_manifest(tmp_root, manifest)


if __name__ == "__main__":
    unittest.main()
