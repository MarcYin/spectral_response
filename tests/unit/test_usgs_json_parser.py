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
from rsrf.manifests import manifest_path
from rsrf.parsers.usgs_json import parse_usgs_json_directory
from rsrf.validate import parse_manifest_dict


def _manifest_for(sensor_unit_id: str) -> dict:
    payload = read_json(manifest_path(ROOT, "rsrf_source_manifest_sentinel2c_v2.json"))
    payload["source_id"] = f"{sensor_unit_id}_usgs_json_test"
    payload["sensor_unit_id"] = sensor_unit_id
    payload["title"] = f"{sensor_unit_id} test source"
    payload["url"] = "https://landsat.usgs.gov/spectral-characteristics-viewer"
    payload["doc_version"] = "c3-master"
    payload["raw_local_path"] = "sources/raw/test"
    payload["file_sha256"] = "test"
    payload["parser"]["script"] = "scripts/ingest/ingest_sampled_curve.py"
    payload["parser"]["entrypoint"] = "parse_usgs_json_directory"
    payload["validation"]["plot_overlay_required"] = False
    return payload


class UsgsJsonParserTests(unittest.TestCase):
    def test_parser_extracts_landsat_band_curves(self) -> None:
        manifest = parse_manifest_dict(_manifest_for("landsat-8_oli"))
        payloads = {
            "Landsat8OLI2.json": [
                {"Landsat 8 OLI": 0.50, "L8OLI-2": 0.0},
                {"Landsat 8 OLI": 0.51, "L8OLI-2": 1.0},
                {"Landsat 8 OLI": 0.52, "L8OLI-2": 0.0},
            ],
            "Landsat8OLI1.json": [
                {"Landsat 8 OLI": 0.43, "L8OLI-1": 0.0},
                {"Landsat 8 OLI": 0.44, "L8OLI-1": 1.0},
                {"Landsat 8 OLI": 0.45, "L8OLI-1": 0.0},
            ],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            source_dir = Path(tmpdir)
            for filename, payload in payloads.items():
                (source_dir / filename).write_text(json.dumps(payload), encoding="utf-8")
            artifacts = parse_usgs_json_directory(source_dir, manifest)

        self.assertEqual(len(artifacts.band_rows), 2)
        self.assertEqual(artifacts.band_rows[0]["band_id"], "B1")
        self.assertEqual(artifacts.band_rows[1]["band_id"], "B2")
        self.assertEqual(artifacts.curve_rows[0]["wavelength_nm"], 430.0)

    def test_parser_handles_aster_stereo_band_labels(self) -> None:
        manifest = parse_manifest_dict(_manifest_for("terra_aster"))
        payloads = {
            "TerraASTER3N.json": [
                {"Terra ASTER": 0.72, "TerraA-3N": 0.0},
                {"Terra ASTER": 0.73, "TerraA-3N": 1.0},
                {"Terra ASTER": 0.74, "TerraA-3N": 0.0},
            ],
            "TerraASTER3B.json": [
                {"Terra ASTER": 0.72, "TerraA-3B": 0.0},
                {"Terra ASTER": 0.73, "TerraA-3B": 1.0},
                {"Terra ASTER": 0.74, "TerraA-3B": 0.0},
            ],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            source_dir = Path(tmpdir)
            for filename, payload in payloads.items():
                (source_dir / filename).write_text(json.dumps(payload), encoding="utf-8")
            artifacts = parse_usgs_json_directory(source_dir, manifest)

        self.assertEqual([row["band_id"] for row in artifacts.band_rows], ["B3N", "B3B"])
        self.assertEqual([row["band_index"] for row in artifacts.band_rows], [3, 4])


if __name__ == "__main__":
    unittest.main()
