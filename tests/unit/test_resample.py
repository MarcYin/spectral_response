from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rsrf.models import SampledCurve
from rsrf.resample import resample_curve


class ResampleCurveTests(unittest.TestCase):
    def _make_curve(self) -> SampledCurve:
        return SampledCurve(
            band_id="B01",
            wavelength_nm=np.array([400.0, 500.0, 600.0]),
            response=np.array([0.0, 1.0, 0.0]),
        )

    def test_identity_resample(self) -> None:
        curve = self._make_curve()
        target = np.array([400.0, 500.0, 600.0])
        result = resample_curve(curve, target)
        np.testing.assert_array_almost_equal(result.response, curve.response)
        self.assertEqual(result.band_id, "B01")

    def test_interpolated_grid(self) -> None:
        curve = self._make_curve()
        target = np.array([450.0, 500.0, 550.0])
        result = resample_curve(curve, target)
        self.assertAlmostEqual(float(result.response[0]), 0.5)
        self.assertAlmostEqual(float(result.response[1]), 1.0)
        self.assertAlmostEqual(float(result.response[2]), 0.5)

    def test_extrapolation_returns_zero(self) -> None:
        curve = self._make_curve()
        target = np.array([300.0, 700.0])
        result = resample_curve(curve, target)
        np.testing.assert_array_equal(result.response, [0.0, 0.0])

    def test_preserves_source_variant(self) -> None:
        curve = SampledCurve(
            band_id="B01",
            wavelength_nm=np.array([400.0, 500.0]),
            response=np.array([1.0, 1.0]),
            source_variant="original",
        )
        result = resample_curve(curve, np.array([450.0]))
        self.assertEqual(result.source_variant, "original")


if __name__ == "__main__":
    unittest.main()
