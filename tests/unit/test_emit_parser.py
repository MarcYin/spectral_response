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
from rsrf.parsers.emit import parse_emit_band_parameters_ascii
from rsrf.validate import parse_manifest_dict


def _manifest_payload() -> dict:
    payload = read_json(ROOT / "rsrf_source_manifest_hyperspectral_band_spec_example.json")
    payload["source_id"] = "emit_ascii_test"
    payload["sensor_unit_id"] = "emit_hsi"
    payload["title"] = "EMIT ASCII parser test"
    payload["url"] = "https://opendap.earthdata.nasa.gov/"
    payload["doc_version"] = "test"
    payload["raw_local_path"] = "sources/raw/test_emit.ascii"
    payload["file_sha256"] = "test"
    payload["parser"]["script"] = "scripts/ingest/ingest_band_spec_table.py"
    payload["parser"]["entrypoint"] = "parse_emit_band_parameters_ascii"
    payload["validation"]["expected_band_count"] = 3
    return payload


class EmitParserTests(unittest.TestCase):
    def test_parse_emit_band_parameters_ascii_extracts_status_flags(self) -> None:
        manifest = parse_manifest_dict(_manifest_payload())
        with tempfile.TemporaryDirectory() as tmpdir:
            source_path = Path(tmpdir) / "fixture.ascii"
            source_path.write_text(
                "\n".join(
                    [
                        "Dataset: test.nc",
                        "/sensor_band_parameters/wavelengths, 400.0, 410.0, 420.0",
                        "/sensor_band_parameters/fwhm, 8.4, 8.5, 8.6",
                        "/sensor_band_parameters/good_wavelengths, 1, 0, 1",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            artifacts = parse_emit_band_parameters_ascii(source_path, manifest)

        self.assertEqual(len(artifacts.band_spec_rows), 3)
        self.assertEqual(artifacts.band_spec_rows[0]["band_id"], "B001")
        self.assertEqual(artifacts.band_spec_rows[1]["band_status"], "non_science")
        self.assertAlmostEqual(artifacts.band_rows[2]["fwhm_nm"], 8.6)


if __name__ == "__main__":
    unittest.main()
