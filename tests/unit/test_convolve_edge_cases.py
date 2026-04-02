from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rsrf.convolve import convolution_weights, convolve_spectrum, response_area
from rsrf.models import SampledCurve


class ResponseAreaTests(unittest.TestCase):
    def test_triangular_curve(self) -> None:
        curve = SampledCurve(
            band_id="T",
            wavelength_nm=np.array([0.0, 1.0, 2.0]),
            response=np.array([0.0, 1.0, 0.0]),
        )
        self.assertAlmostEqual(response_area(curve), 1.0)

    def test_flat_curve(self) -> None:
        curve = SampledCurve(
            band_id="F",
            wavelength_nm=np.array([100.0, 200.0]),
            response=np.array([1.0, 1.0]),
        )
        self.assertAlmostEqual(response_area(curve), 100.0)


class ConvolveSpectrumEdgeCases(unittest.TestCase):
    def test_zero_response_raises(self) -> None:
        curve = SampledCurve(
            band_id="Z",
            wavelength_nm=np.array([400.0, 500.0]),
            response=np.array([0.0, 0.0]),
        )
        with self.assertRaises(ValueError, msg="zero area"):
            convolve_spectrum(
                np.array([400.0, 500.0]),
                np.array([1.0, 1.0]),
                curve,
            )


class ConvolutionWeightsEdgeCases(unittest.TestCase):
    def test_no_overlap_raises(self) -> None:
        curve = SampledCurve(
            band_id="B",
            wavelength_nm=np.array([400.0, 500.0]),
            response=np.array([1.0, 1.0]),
        )
        with self.assertRaises(ValueError, msg="does not overlap"):
            convolution_weights(np.array([700.0, 800.0]), curve)

    def test_one_dimensional_check(self) -> None:
        curve = SampledCurve(
            band_id="B",
            wavelength_nm=np.array([400.0, 500.0]),
            response=np.array([1.0, 1.0]),
        )
        with self.assertRaises(ValueError):
            convolution_weights(np.array([[400.0, 500.0]]), curve)

    def test_non_increasing_raises(self) -> None:
        curve = SampledCurve(
            band_id="B",
            wavelength_nm=np.array([400.0, 500.0]),
            response=np.array([1.0, 1.0]),
        )
        with self.assertRaises(ValueError):
            convolution_weights(np.array([500.0, 400.0]), curve)


if __name__ == "__main__":
    unittest.main()
