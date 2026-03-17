from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rsrf.io import read_json
from rsrf.manifests import manifest_path
from rsrf.parsers.band_spec_table import parse_band_spec_table
from rsrf.validate import parse_manifest_dict


class BandSpecParserTests(unittest.TestCase):
    def test_parser_extracts_band_specs_and_metadata(self) -> None:
        payload = read_json(manifest_path(ROOT, "rsrf_source_manifest_hyperspectral_band_spec_example.json"))
        manifest = parse_manifest_dict(payload)
        table_path = ROOT / manifest.raw_local_path
        artifacts = parse_band_spec_table(table_path, manifest)

        self.assertEqual(len(artifacts.band_spec_rows), 6)
        self.assertEqual(len(artifacts.band_rows), 6)
        self.assertEqual(artifacts.band_spec_rows[0]["band_id"], "B001")
        self.assertEqual(artifacts.band_rows[3]["band_status"], "masked")
        self.assertEqual(artifacts.metadata["band_spec_table"]["row_count"], 6)


if __name__ == "__main__":
    unittest.main()
