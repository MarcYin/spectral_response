from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rsrf.band_specs import build_band_spec
from rsrf.realize import (
    estimate_center_wavelength,
    estimate_fwhm,
    gaussian_curve_from_band_spec,
)


class RealizationTests(unittest.TestCase):
    def test_gaussian_realization_recovers_center_and_peak(self) -> None:
        band_spec = build_band_spec(705.0, 15.0, band_index=1)
        curve = gaussian_curve_from_band_spec(band_spec)
        self.assertGreater(len(curve.wavelength_nm), 10)
        self.assertAlmostEqual(max(curve.response), 1.0, places=6)
        self.assertAlmostEqual(estimate_center_wavelength(curve), 705.0, places=6)

    def test_gaussian_realization_approximates_fwhm(self) -> None:
        band_spec = build_band_spec(865.0, 20.0, band_index=2)
        curve = gaussian_curve_from_band_spec(band_spec)
        self.assertAlmostEqual(estimate_fwhm(curve), 20.0, delta=1.0)


if __name__ == "__main__":
    unittest.main()
