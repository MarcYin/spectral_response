"""Basic convolution helpers for realized response curves."""

from __future__ import annotations

import numpy as np

from .models import SampledCurve


def response_area(curve: SampledCurve) -> float:
    """Return the integral of a sampled response curve."""

    wavelength_nm = np.asarray(curve.wavelength_nm, dtype=float)
    response = np.asarray(curve.response, dtype=float)
    return float(np.trapz(response, wavelength_nm))


def convolve_spectrum(
    spectrum_wavelength_nm: np.ndarray,
    spectrum_values: np.ndarray,
    curve: SampledCurve,
) -> float:
    """Convolve a spectrum with a sampled response curve."""

    spectrum_wavelength_nm = np.asarray(spectrum_wavelength_nm, dtype=float)
    spectrum_values = np.asarray(spectrum_values, dtype=float)
    curve_wavelength_nm = np.asarray(curve.wavelength_nm, dtype=float)
    curve_response = np.asarray(curve.response, dtype=float)
    sampled_spectrum = np.interp(
        curve_wavelength_nm,
        spectrum_wavelength_nm,
        spectrum_values,
        left=0.0,
        right=0.0,
    )
    numerator = float(np.trapz(sampled_spectrum * curve_response, curve_wavelength_nm))
    denominator = float(np.trapz(curve_response, curve_wavelength_nm))
    if denominator == 0.0:
        raise ValueError("response curve has zero area")
    return numerator / denominator
