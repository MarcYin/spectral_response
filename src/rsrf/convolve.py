"""Basic convolution helpers for realized response curves."""

from __future__ import annotations

import numpy as np

from .models import BandSpec, SampledCurve
from .realize import realize_curve


def response_area(curve: SampledCurve) -> float:
    """Return the integral of a sampled response curve."""

    wavelength_nm = np.asarray(curve.wavelength_nm, dtype=float)
    response = np.asarray(curve.response, dtype=float)
    return _integrate(response, wavelength_nm)


def convolve_spectrum(
    spectrum_wavelength_nm: np.ndarray,
    spectrum_values: np.ndarray,
    response_definition: SampledCurve | BandSpec,
) -> float:
    """Convolve a spectrum with a sampled curve or a band specification."""

    spectrum_wavelength_nm = np.asarray(spectrum_wavelength_nm, dtype=float)
    spectrum_values = np.asarray(spectrum_values, dtype=float)
    curve = _as_curve(response_definition)
    curve_wavelength_nm = np.asarray(curve.wavelength_nm, dtype=float)
    curve_response = np.asarray(curve.response, dtype=float)
    sampled_spectrum = np.interp(
        curve_wavelength_nm,
        spectrum_wavelength_nm,
        spectrum_values,
        left=0.0,
        right=0.0,
    )
    numerator = _integrate(sampled_spectrum * curve_response, curve_wavelength_nm)
    denominator = _integrate(curve_response, curve_wavelength_nm)
    if denominator == 0.0:
        raise ValueError("response curve has zero area")
    return numerator / denominator


def convolution_weights(
    spectrum_wavelength_nm: np.ndarray,
    response_definition: SampledCurve | BandSpec,
) -> np.ndarray:
    """Build normalized response weights on a target spectral grid."""

    spectrum_wavelength_nm = np.asarray(spectrum_wavelength_nm, dtype=float)
    if spectrum_wavelength_nm.ndim != 1 or spectrum_wavelength_nm.size < 2:
        raise ValueError("spectrum_wavelength_nm must be a one-dimensional grid with at least two points")
    if not np.all(np.diff(spectrum_wavelength_nm) > 0):
        raise ValueError("spectrum_wavelength_nm must be strictly increasing")
    curve = _as_curve(response_definition)
    curve_wavelength_nm = np.asarray(curve.wavelength_nm, dtype=float)
    curve_response = np.asarray(curve.response, dtype=float)
    response = np.interp(
        spectrum_wavelength_nm,
        curve_wavelength_nm,
        curve_response,
        left=0.0,
        right=0.0,
    )
    weights = response * _interval_widths(spectrum_wavelength_nm)
    total = float(weights.sum())
    if total == 0.0:
        raise ValueError("response definition does not overlap the provided spectrum grid")
    return weights / total


def _as_curve(response_definition: SampledCurve | BandSpec) -> SampledCurve:
    if isinstance(response_definition, SampledCurve):
        return response_definition
    if isinstance(response_definition, BandSpec):
        return realize_curve(response_definition)
    raise TypeError(f"unsupported response definition type: {type(response_definition)!r}")


def _integrate(values: np.ndarray, wavelength_nm: np.ndarray) -> float:
    trapezoid = getattr(np, "trapezoid", np.trapz)
    return float(trapezoid(values, wavelength_nm))


def _interval_widths(wavelength_nm: np.ndarray) -> np.ndarray:
    widths = np.empty_like(wavelength_nm, dtype=float)
    widths[0] = (wavelength_nm[1] - wavelength_nm[0]) / 2.0
    widths[-1] = (wavelength_nm[-1] - wavelength_nm[-2]) / 2.0
    widths[1:-1] = (wavelength_nm[2:] - wavelength_nm[:-2]) / 2.0
    return widths
