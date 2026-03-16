from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rsrf.api import (
    get_metadata,
    list_bands,
    list_sensors,
    load_band_spec,
    load_curve,
    load_response_definition,
)
from rsrf.models import BandSpec, SampledCurve


class ApiTests(unittest.TestCase):
    def test_list_sensors_returns_both_canonical_forms(self) -> None:
        sensors = list_sensors(ROOT)
        variants = {
            (row["sensor_unit_id"], row["representation_variant"])
            for row in sensors
        }
        self.assertEqual(
            variants,
            {
                ("sentinel-2c_msi", "band_average"),
                ("hyperspec_example", "metadata_band_spec"),
            },
        )

    def test_load_curve_reads_canonical_sampled_data(self) -> None:
        curve = load_curve("sentinel-2c_msi", "B01", "band_average", root=ROOT)
        self.assertIsInstance(curve, SampledCurve)
        self.assertEqual(curve.band_id, "B01")
        self.assertEqual(len(curve.wavelength_nm), 2301)

    def test_load_band_spec_reads_canonical_band_spec(self) -> None:
        band_spec = load_band_spec(
            "hyperspec_example",
            "B001",
            "metadata_band_spec",
            root=ROOT,
        )
        self.assertIsInstance(band_spec, BandSpec)
        self.assertEqual(band_spec.band_id, "B001")
        self.assertAlmostEqual(band_spec.center_wavelength_nm, 410.0)

    def test_load_response_definition_dispatches_by_content_kind(self) -> None:
        sampled = load_response_definition("sentinel-2c_msi", "B02", "band_average", root=ROOT)
        band_spec = load_response_definition(
            "hyperspec_example",
            "B002",
            "metadata_band_spec",
            root=ROOT,
        )
        self.assertIsInstance(sampled, SampledCurve)
        self.assertIsInstance(band_spec, BandSpec)

    def test_unbacked_realized_variant_is_not_exposed_by_read_api(self) -> None:
        with self.assertRaises(KeyError):
            load_response_definition(
                "hyperspec_example",
                "B001",
                "gaussian_from_fwhm",
                root=ROOT,
            )

    def test_list_bands_and_metadata_use_registry_outputs(self) -> None:
        sentinel_bands = list_bands("sentinel-2c_msi", "band_average", root=ROOT)
        hyperspec_metadata = get_metadata(
            "hyperspec_example",
            "metadata_band_spec",
            root=ROOT,
        )
        self.assertEqual(len(sentinel_bands), 13)
        self.assertEqual(hyperspec_metadata["band_spec_table"]["row_count"], 6)


if __name__ == "__main__":
    unittest.main()
