from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rsrf.io import read_json
from rsrf.parsers.probav import parse_probav_srf_workbook
from rsrf.validate import parse_manifest_dict


def _manifest_payload() -> dict:
    payload = read_json(ROOT / "rsrf_source_manifest_sentinel2c_v2.json")
    payload["source_id"] = "probav_srf_test"
    payload["sensor_unit_id"] = "probav_vgt"
    payload["representation_variant"] = "left_camera"
    payload["title"] = "PROBA-V workbook parser test"
    payload["url"] = "https://proba-v.vgt.vito.be/en/quality/spectral-response-functions"
    payload["doc_version"] = "test"
    payload["raw_local_path"] = "sources/raw/test_probav.xlsx"
    payload["file_sha256"] = "test"
    payload["parser"]["script"] = "scripts/ingest/ingest_sampled_curve.py"
    payload["parser"]["entrypoint"] = "parse_probav_srf_workbook"
    payload["validation"]["expected_band_count"] = 4
    payload["validation"]["plot_overlay_required"] = False
    return payload


class ProbavParserTests(unittest.TestCase):
    def test_parse_probav_srf_workbook_selects_requested_camera(self) -> None:
        manifest = parse_manifest_dict(_manifest_payload())
        with tempfile.TemporaryDirectory() as tmpdir:
            workbook_path = Path(tmpdir) / "fixture.xlsx"
            workbook = Workbook()
            worksheet = workbook.active
            worksheet.title = "Proba-V"
            worksheet.append(
                [
                    "wvl_BLUE",
                    "BLUE CENTER",
                    "BLUE LEFT",
                    "BLUE RIGHT",
                    None,
                    "wvl_RED",
                    "RED CENTER",
                    "RED LEFT",
                    "RED RIGHT",
                    None,
                    "wvl_NIR",
                    "NIR CENTER",
                    "NIR LEFT",
                    "NIR RIGHT",
                    None,
                    "wvl_SWIR",
                    "SWIR CENTER",
                    "SWIR LEFT",
                    "SWIR RIGHT",
                ]
            )
            worksheet.append([400, 0.1, 0.2, 0.3, None, 600, 0.4, 0.5, 0.6, None, 800, 0.7, 0.8, 0.9, None, 1600, 0.2, 0.3, 0.4])
            worksheet.append([405, 0.0, 0.1, 0.0, None, 605, 0.1, 0.2, 0.3, None, 805, 0.4, 0.5, 0.6, None, 1605, 0.0, 0.1, 0.2])
            workbook.save(workbook_path)

            artifacts = parse_probav_srf_workbook(workbook_path, manifest)

        self.assertEqual(len(artifacts.band_rows), 4)
        blue_rows = [row for row in artifacts.curve_rows if row["band_id"] == "BLUE"]
        red_rows = [row for row in artifacts.curve_rows if row["band_id"] == "RED"]
        self.assertEqual(len(blue_rows), 2)
        self.assertEqual(blue_rows[0]["response"], 0.2)
        self.assertEqual(red_rows[0]["response"], 0.5)


if __name__ == "__main__":
    unittest.main()
