from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rsrf.io import read_json
from rsrf.ingest import write_band_spec_artifacts
from rsrf.parsers.band_spec_table import parse_band_spec_table
from rsrf.registry import read_registry_table
from rsrf.validate import parse_manifest_dict


class BandSpecIngestTests(unittest.TestCase):
    def test_write_band_spec_artifacts_updates_registry(self) -> None:
        payload = read_json(ROOT / "rsrf_source_manifest_hyperspectral_band_spec_example.json")
        manifest = parse_manifest_dict(payload)
        artifacts = parse_band_spec_table(ROOT / manifest.raw_local_path, manifest)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            written = write_band_spec_artifacts(tmp_root, manifest, artifacts)
            self.assertIn("band_specs", written)
            band_specs = read_registry_table(tmp_root, "band_specs")
            realizations = read_registry_table(tmp_root, "realizations")
            self.assertEqual(len(band_specs), 6)
            self.assertEqual(len(realizations), 1)
            metadata = json.loads((tmp_root / "data" / "canonical" / "band_spec" / manifest.sensor_unit_id / manifest.representation_variant / "metadata.json").read_text())
            self.assertEqual(metadata["band_spec_table"]["row_count"], 6)


if __name__ == "__main__":
    unittest.main()
