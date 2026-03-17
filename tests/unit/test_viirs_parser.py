from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rsrf.io import read_json
from rsrf.manifests import manifest_path
from rsrf.parsers.viirs import parse_viirs_band_average_zip
from rsrf.validate import parse_manifest_dict


def _manifest_for(sensor_unit_id: str) -> dict:
    payload = read_json(manifest_path(ROOT, "rsrf_source_manifest_sentinel2c_v2.json"))
    payload["source_id"] = f"{sensor_unit_id}_viirs_test"
    payload["sensor_unit_id"] = sensor_unit_id
    payload["title"] = f"{sensor_unit_id} VIIRS test source"
    payload["url"] = "https://ncc.nesdis.noaa.gov/VIIRS/VIIRSSpectralResponseFunctions.php"
    payload["doc_version"] = "test"
    payload["raw_local_path"] = "sources/raw/test.zip"
    payload["file_sha256"] = "test"
    payload["parser"]["script"] = "scripts/ingest/ingest_sampled_curve.py"
    payload["parser"]["entrypoint"] = "parse_viirs_band_average_zip"
    payload["validation"]["plot_overlay_required"] = False
    payload["validation"]["monotonic_centers_required"] = False
    payload["validation"]["expected_band_count"] = 2
    return payload


class ViirsParserTests(unittest.TestCase):
    def test_parser_selects_highest_priority_band_average_members(self) -> None:
        manifest = parse_manifest_dict(_manifest_for("noaa-20_viirs"))
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = Path(tmpdir) / "viirs.zip"
            with ZipFile(zip_path, "w") as archive:
                archive.writestr(
                    "J1_VIIRS_V1_RSR_used_in_V2/J1_VIIRS_RSR_M1_BA_V1F.txt",
                    "# old\n M1 400.0 0.0\n M1 410.0 0.5\n M1 420.0 0.0\n",
                )
                archive.writestr(
                    "J1_VIIRS_BA_RSR_V2F/J1_VIIRS_RSR_M1_BA_Fused_V2F.txt",
                    "# new\n M1 400.0 0.0\n M1 410.0 1.0\n M1 420.0 0.0\n",
                )
                archive.writestr(
                    "J1_VIIRS_BA_RSR_V2F/J1_VIIRS_RSR_I1_BA_Fused_V2F.txt",
                    "% comment\n I1 600.0 0.0\n I1 610.0 1.0\n I1 620.0 0.0\n",
                )
                archive.writestr(
                    "J1_VIIRS_BA_RSR_V2F/J1_VIIRS_RSR_M16A_BA_V2F.txt",
                    "M16A 11800.0 0.0\nM16A 11810.0 1.0\nM16A 11820.0 0.0\n",
                )
                archive.writestr(
                    "J1_VIIRS_BA_RSR_V2F/J1_VIIRS_RSR_M16B_BA_V2F.txt",
                    "M16B 12000.0 0.0\nM16B 12010.0 1.0\nM16B 12020.0 0.0\n",
                )
                archive.writestr(
                    "J1_VIIRS_BA_RSR_V2F/J1_VIIRS_RSR_M16_BA_V2F.txt",
                    "M16 11900.0 0.0\nM16 11910.0 1.0\nM16 11920.0 0.0\n",
                )
                archive.writestr(
                    "J1_VIIRS_Detector_RSR_V2/J1_VIIRS_RSR_M1_Detector_Fused_V2.txt",
                    "ignored\n",
                )
                archive.writestr(
                    "J1_VIIRS_BA_RSR_V2F/._J1_VIIRS_RSR_M2_BA_Fused_V2F.txt",
                    "bad\n",
                )
            artifacts = parse_viirs_band_average_zip(zip_path, manifest)

        self.assertEqual(len(artifacts.band_rows), 4)
        m1_rows = [row for row in artifacts.curve_rows if row["band_id"] == "M1"]
        self.assertEqual(m1_rows[1]["response"], 1.0)
        self.assertEqual([row["band_id"] for row in artifacts.band_rows], ["M1", "M16A", "M16B", "I1"])


if __name__ == "__main__":
    unittest.main()
