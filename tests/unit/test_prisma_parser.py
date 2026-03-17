from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import h5py

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rsrf.io import read_json
from rsrf.parsers.prisma import parse_prisma_he5_metadata
from rsrf.validate import parse_manifest_dict


def _manifest_payload() -> dict:
    payload = read_json(ROOT / "rsrf_source_manifest_hyperspectral_band_spec_example.json")
    payload["source_id"] = "prisma_he5_test"
    payload["sensor_unit_id"] = "prisma_hsi"
    payload["title"] = "PRISMA parser test"
    payload["url"] = "https://www.asi.it/en/earth-science/prisma/"
    payload["doc_version"] = "test"
    payload["raw_local_path"] = "sources/raw/test_prisma.he5"
    payload["file_sha256"] = "test"
    payload["mission_family"] = "PRISMA"
    payload["platform"] = "PRISMA"
    payload["instrument"] = "HSI"
    payload["parser"]["script"] = "scripts/ingest/ingest_band_spec_table.py"
    payload["parser"]["entrypoint"] = "parse_prisma_he5_metadata"
    payload["validation"]["expected_band_count"] = 4
    payload["validation"]["monotonic_centers_required"] = False
    return payload


class PrismaParserTests(unittest.TestCase):
    def test_parse_prisma_he5_metadata_extracts_valid_band_lists(self) -> None:
        manifest = parse_manifest_dict(_manifest_payload())
        with tempfile.TemporaryDirectory() as tmpdir:
            source_path = Path(tmpdir) / "fixture.he5"
            with h5py.File(source_path, "w") as handle:
                handle.attrs["Product_ID"] = b"PRS_L1_STD"
                handle.attrs["Product_Name"] = b"fixture.he5"
                handle.attrs["Processing_Level"] = b"1"
                handle.attrs["Image_ID"] = 7
                handle.attrs["List_Cw_Vnir"] = [1000.0, 900.0]
                handle.attrs["List_Fwhm_Vnir"] = [12.5, 12.0]
                handle.attrs["List_Cw_Swir"] = [2500.0, 2400.0, 0.0]
                handle.attrs["List_Fwhm_Swir"] = [9.5, 9.0, 0.0]

            artifacts = parse_prisma_he5_metadata(source_path, manifest)

        self.assertEqual(len(artifacts.band_spec_rows), 4)
        self.assertEqual(artifacts.band_spec_rows[0]["band_id"], "B001")
        self.assertEqual(artifacts.band_rows[2]["band_name"], "SWIR001")
        self.assertAlmostEqual(artifacts.band_rows[3]["center_wavelength_nm"], 2400.0)
        self.assertEqual(artifacts.metadata["band_spec_table"]["subsystem_counts"]["VNIR"], 2)
        self.assertEqual(artifacts.metadata["band_spec_table"]["subsystem_counts"]["SWIR"], 2)
        self.assertEqual(artifacts.metadata["band_spec_table"]["dropped_invalid_slots"]["SWIR"], 1)


if __name__ == "__main__":
    unittest.main()
