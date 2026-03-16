from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rsrf.band_specs import build_band_spec
from rsrf.models import GridPolicy
from rsrf.realize import (
    estimate_center_wavelength,
    estimate_fwhm,
    gaussian_curve_from_band_spec,
    realize_curve,
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

    def test_realize_curve_accepts_grid_policy_and_variant(self) -> None:
        band_spec = build_band_spec(560.0, 12.0, band_index=3)
        grid_policy = GridPolicy(
            kind="adaptive_per_band",
            samples_per_fwhm=12,
            max_step_nm=0.5,
            truncate_sigma=5.0,
        )
        curve = realize_curve(
            band_spec,
            grid_policy=grid_policy,
            source_variant="gaussian_from_fwhm",
        )
        self.assertEqual(curve.source_variant, "gaussian_from_fwhm")
        self.assertGreater(len(curve.wavelength_nm), 20)

    def test_realize_curve_rejects_unsupported_profile(self) -> None:
        band_spec = build_band_spec(560.0, 12.0, band_index=3)
        with self.assertRaises(NotImplementedError):
            realize_curve(band_spec, profile_type="triangle")


if __name__ == "__main__":
    unittest.main()
