from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rsrf.io import read_json
from rsrf.registry import manifest_registry_rows
from rsrf.validate import parse_manifest_dict


class RegistryRowTests(unittest.TestCase):
    def test_sampled_curve_manifest_produces_sensor_and_source_rows(self) -> None:
        payload = read_json(ROOT / "rsrf_source_manifest_sentinel2c_v2.json")
        manifest = parse_manifest_dict(payload)
        rows = manifest_registry_rows(manifest)
        self.assertEqual(len(rows["sensors"]), 1)
        self.assertEqual(len(rows["sources"]), 1)
        self.assertEqual(rows["realizations"], [])
        self.assertEqual(rows["sensors"][0]["content_kind"], "sampled_curve")
        self.assertEqual(rows["sensors"][0]["mission_family"], "Sentinel-2")
        self.assertEqual(rows["sensors"][0]["platform"], "Sentinel-2C")
        self.assertEqual(rows["sensors"][0]["instrument"], "MSI")

    def test_band_spec_manifest_produces_realization_row(self) -> None:
        payload = read_json(ROOT / "rsrf_source_manifest_hyperspectral_band_spec_example.json")
        manifest = parse_manifest_dict(payload)
        rows = manifest_registry_rows(manifest)
        self.assertEqual(len(rows["sensors"]), 2)
        self.assertEqual(len(rows["realizations"]), 1)
        realized_sensor = next(
            row
            for row in rows["sensors"]
            if row["representation_variant"] == "gaussian_from_fwhm"
        )
        self.assertEqual(realized_sensor["content_kind"], "sampled_curve")
        self.assertEqual(realized_sensor["realization_kind"], "approximate_parametric")
        self.assertTrue(realized_sensor["approximation"])
        realization = rows["realizations"][0]
        self.assertEqual(realization["output_representation_variant"], "gaussian_from_fwhm")
        self.assertTrue(realization["approximation"])
        self.assertEqual(
            json.loads(realization["grid_policy"])["samples_per_fwhm"],
            10,
        )


if __name__ == "__main__":
    unittest.main()
