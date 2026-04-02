from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rsrf.band_specs import build_band_spec, default_band_id
from rsrf.models import BandSpec


class DefaultBandIdTests(unittest.TestCase):
    def test_zero_padded_format(self) -> None:
        self.assertEqual(default_band_id(0), "B000")
        self.assertEqual(default_band_id(1), "B001")
        self.assertEqual(default_band_id(99), "B099")
        self.assertEqual(default_band_id(100), "B100")

    def test_negative_index_raises(self) -> None:
        with self.assertRaises(ValueError):
            default_band_id(-1)


class BuildBandSpecTests(unittest.TestCase):
    def test_basic_construction(self) -> None:
        spec = build_band_spec(550.0, 10.0, band_id="Green")
        self.assertIsInstance(spec, BandSpec)
        self.assertEqual(spec.band_id, "Green")
        self.assertAlmostEqual(spec.center_wavelength_nm, 550.0)
        self.assertAlmostEqual(spec.fwhm_nm, 10.0)

    def test_band_id_from_index(self) -> None:
        spec = build_band_spec(550.0, 10.0, band_index=5)
        self.assertEqual(spec.band_id, "B005")
        self.assertEqual(spec.band_index, 5)

    def test_missing_band_id_and_index_raises(self) -> None:
        with self.assertRaises(ValueError):
            build_band_spec(550.0, 10.0)

    def test_nonpositive_center_raises(self) -> None:
        with self.assertRaises(ValueError):
            build_band_spec(0.0, 10.0, band_id="X")
        with self.assertRaises(ValueError):
            build_band_spec(-1.0, 10.0, band_id="X")

    def test_nonpositive_fwhm_raises(self) -> None:
        with self.assertRaises(ValueError):
            build_band_spec(550.0, 0.0, band_id="X")
        with self.assertRaises(ValueError):
            build_band_spec(550.0, -1.0, band_id="X")

    def test_optional_fields(self) -> None:
        spec = build_band_spec(
            550.0, 10.0,
            band_id="Green",
            band_name="Green Channel",
            band_status="active",
            published_shape_type="gaussian",
        )
        self.assertEqual(spec.band_name, "Green Channel")
        self.assertEqual(spec.band_status, "active")
        self.assertEqual(spec.published_shape_type, "gaussian")


if __name__ == "__main__":
    unittest.main()
