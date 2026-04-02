from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rsrf.api import load_band_spec, load_curve
from rsrf.convolve import convolution_weights, convolve_spectrum
from rsrf.models import SampledCurve


class ConvolveResponseDefinitionTests(unittest.TestCase):
    def test_constant_spectrum_convolution_returns_constant_for_sampled_curve(self) -> None:
        curve = load_curve("sentinel-2c_msi", "B03", "band_average", root=ROOT)
        wavelength_nm = np.linspace(300.0, 2600.0, 2301)
        values = np.full_like(wavelength_nm, 5.0)
        band_value = convolve_spectrum(wavelength_nm, values, curve)
        self.assertAlmostEqual(band_value, 5.0, places=6)

    def test_constant_spectrum_convolution_returns_constant_for_band_spec(self) -> None:
        band_spec = load_band_spec("hyperspec_example", "B003", "metadata_band_spec", root=ROOT)
        wavelength_nm = np.linspace(350.0, 500.0, 1501)
        values = np.full_like(wavelength_nm, 7.0)
        band_value = convolve_spectrum(wavelength_nm, values, band_spec)
        self.assertAlmostEqual(band_value, 7.0, places=6)

    def test_convolution_weights_normalize_to_one(self) -> None:
        band_spec = load_band_spec("hyperspec_example", "B004", "metadata_band_spec", root=ROOT)
        wavelength_nm = np.linspace(350.0, 500.0, 1501)
        weights = convolution_weights(wavelength_nm, band_spec)
        self.assertAlmostEqual(float(weights.sum()), 1.0, places=6)

    def test_convolution_weights_respect_nonuniform_grid_spacing(self) -> None:
        curve = SampledCurve(
            band_id="B001",
            wavelength_nm=np.array([0.0, 1.0, 3.0]),
            response=np.array([1.0, 2.0, 1.0]),
        )
        wavelength_nm = np.array([0.0, 1.0, 3.0])
        values = np.array([2.0, 4.0, 8.0])
        weights = convolution_weights(wavelength_nm, curve)
        band_value = convolve_spectrum(wavelength_nm, values, curve)
        self.assertAlmostEqual(float(np.dot(values, weights)), band_value, places=6)


if __name__ == "__main__":
    unittest.main()
