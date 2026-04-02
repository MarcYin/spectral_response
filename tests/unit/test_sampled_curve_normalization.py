from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rsrf.io import read_json
from rsrf.manifests import manifest_path
from rsrf.parsers.common import ParsedBandCurve, build_sampled_curve_artifacts
from rsrf.validate import parse_manifest_dict


class SampledCurveNormalizationTests(unittest.TestCase):
    def test_build_sampled_curve_artifacts_normalizes_duplicate_and_negative_samples(self) -> None:
        payload = read_json(manifest_path(ROOT, "rsrf_source_manifest_sentinel2c_v2.json"))
        payload["source_id"] = "sampled_curve_normalization_test"
        payload["sensor_unit_id"] = "normalization_test_sensor"
        payload["title"] = "Sampled curve normalization test"
        payload["doc_version"] = "test"
        payload["raw_local_path"] = "sources/raw/test.txt"
        payload["file_sha256"] = "test"
        payload["validation"]["expected_band_count"] = 1
        manifest = parse_manifest_dict(payload)

        artifacts = build_sampled_curve_artifacts(
            manifest,
            ROOT / "README.md",
            [
                ParsedBandCurve(
                    band_id="B01",
                    band_index=1,
                    band_name="B01",
                    wavelength_nm=[420.0, 400.0, 410.0, 410.0],
                    response=[1.2, -0.05, 0.25, 0.5],
                )
            ],
            parser_module="tests.sampled_curve_normalization",
            parser_function="build_sampled_curve_artifacts",
        )

        curve_rows = [
            (row["wavelength_nm"], row["response"]) for row in artifacts.curve_rows if row["band_id"] == "B01"
        ]
        self.assertEqual(
            curve_rows,
            [
                (400.0, 0.0),
                (410.0, 0.5),
                (420.0, 1.0),
            ],
        )
        self.assertEqual(artifacts.metadata["curve_normalization"]["duplicate_wavelength_samples"], 1)
        self.assertEqual(artifacts.metadata["curve_normalization"]["negative_values_clipped"], 1)
        self.assertEqual(artifacts.metadata["curve_normalization"]["values_capped_to_one"], 1)
        self.assertEqual(
            artifacts.metadata["band_metrics"]["B01"]["normalization"]["duplicate_wavelength_samples"],
            1,
        )


if __name__ == "__main__":
    unittest.main()
