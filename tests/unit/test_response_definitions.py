from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rsrf import coerce_response_definition
from rsrf.convolve import convolution_weights, convolve_spectrum, response_area
from rsrf.models import BandSpec, SampledCurve


class ResponseDefinitionCoercionTests(unittest.TestCase):
    def test_coerce_sampled_curve_mapping_returns_sampled_curve(self) -> None:
        response_definition = coerce_response_definition(
            {
                "band_id": "B001",
                "wavelength_nm": [500.0, 510.0, 520.0],
                "response": [0.0, 1.0, 0.0],
            }
        )

        self.assertIsInstance(response_definition, SampledCurve)
        self.assertEqual(response_definition.band_id, "B001")
        self.assertEqual(list(response_definition.wavelength_nm), [500.0, 510.0, 520.0])

    def test_coerce_accepts_sampled_kind_mapping(self) -> None:
        response_definition = coerce_response_definition(
            {
                "kind": "sampled",
                "band_id": "B001",
                "wavelength_nm": [500.0, 510.0, 520.0],
                "response": [0.0, 1.0, 0.0],
            }
        )

        self.assertIsInstance(response_definition, SampledCurve)
        self.assertEqual(response_definition.band_id, "B001")

    def test_coerce_accepts_relative_spectral_response_aliases(self) -> None:
        response_definition = coerce_response_definition(
            {
                "band_id": "B001",
                "wavelength": [500.0, 510.0, 520.0],
                "relative_spectral_response": [0.0, 1.0, 0.0],
            }
        )

        self.assertIsInstance(response_definition, SampledCurve)
        self.assertEqual(response_definition.band_id, "B001")
        self.assertEqual(list(response_definition.wavelength_nm), [500.0, 510.0, 520.0])

    def test_coerce_band_spec_mapping_returns_band_spec(self) -> None:
        response_definition = coerce_response_definition(
            {
                "band_id": "B002",
                "center_wavelength_nm": 560.0,
                "fwhm_nm": 35.0,
                "band_name": "Green",
            }
        )

        self.assertIsInstance(response_definition, BandSpec)
        self.assertEqual(response_definition.band_id, "B002")
        self.assertEqual(response_definition.band_name, "Green")
        self.assertEqual(response_definition.center_wavelength_nm, 560.0)
        self.assertEqual(response_definition.fwhm_nm, 35.0)

    def test_coerce_accepts_gaussian_kind_mapping(self) -> None:
        response_definition = coerce_response_definition(
            {
                "kind": "gaussian",
                "band_id": "B002",
                "center_wavelength_nm": 560.0,
                "fwhm_nm": 35.0,
            }
        )

        self.assertIsInstance(response_definition, BandSpec)
        self.assertEqual(response_definition.band_id, "B002")

    def test_coerce_accepts_center_wavelength_alias(self) -> None:
        response_definition = coerce_response_definition(
            {
                "band_id": "B002",
                "center_wavelength": 560.0,
                "fwhm": 35.0,
            }
        )

        self.assertIsInstance(response_definition, BandSpec)
        self.assertEqual(response_definition.band_id, "B002")
        self.assertEqual(response_definition.center_wavelength_nm, 560.0)
        self.assertEqual(response_definition.fwhm_nm, 35.0)

    def test_coerce_zero_arg_callable_returns_supported_definition(self) -> None:
        response_definition = coerce_response_definition(
            lambda: {
                "band_id": "B003",
                "center_wavelength_nm": 665.0,
                "fwhm_nm": 30.0,
            }
        )

        self.assertIsInstance(response_definition, BandSpec)
        self.assertEqual(response_definition.band_id, "B003")

    def test_coerce_rejects_ambiguous_mapping(self) -> None:
        with self.assertRaisesRegex(ValueError, "either sampled points or center_wavelength_nm"):
            coerce_response_definition(
                {
                    "wavelength_nm": [500.0, 510.0, 520.0],
                    "response": [0.0, 1.0, 0.0],
                    "center_wavelength_nm": 510.0,
                    "fwhm_nm": 10.0,
                }
            )

    def test_coerce_rejects_non_monotonic_wavelengths(self) -> None:
        with self.assertRaisesRegex(ValueError, "strictly increasing"):
            coerce_response_definition(
                {
                    "wavelength_nm": [500.0, 495.0, 520.0],
                    "response": [0.0, 1.0, 0.0],
                }
            )

    def test_coerce_rejects_unknown_kind(self) -> None:
        with self.assertRaisesRegex(ValueError, "unsupported response_definition kind"):
            coerce_response_definition(
                {
                    "kind": "triangle",
                    "center_wavelength_nm": 560.0,
                    "fwhm_nm": 35.0,
                }
            )


class ResponseDefinitionConvolutionTests(unittest.TestCase):
    def test_convolve_accepts_sampled_curve_mapping(self) -> None:
        wavelength_nm = np.array([500.0, 510.0, 520.0], dtype=float)
        values = np.array([5.0, 5.0, 5.0], dtype=float)

        band_value = convolve_spectrum(
            wavelength_nm,
            values,
            {
                "band_id": "B001",
                "wavelength_nm": wavelength_nm,
                "response": np.array([0.0, 1.0, 0.0], dtype=float),
            },
        )

        self.assertAlmostEqual(band_value, 5.0, places=6)

    def test_convolution_weights_accept_band_spec_mapping(self) -> None:
        wavelength_nm = np.linspace(500.0, 600.0, 1001)

        weights = convolution_weights(
            wavelength_nm,
            {
                "band_id": "B002",
                "center_wavelength_nm": 550.0,
                "fwhm_nm": 20.0,
            },
        )

        self.assertAlmostEqual(float(weights.sum()), 1.0, places=6)

    def test_response_area_accepts_callable(self) -> None:
        area = response_area(
            lambda: {
                "band_id": "B003",
                "wavelength_nm": [600.0, 610.0, 620.0],
                "response": [0.0, 1.0, 0.0],
            }
        )

        self.assertGreater(area, 0.0)


if __name__ == "__main__":
    unittest.main()
