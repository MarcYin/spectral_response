"""Basic convolution helpers for realized response curves."""

from __future__ import annotations

import numpy as np

from .models import SampledCurve
from .realize import realize_curve
from .response_definitions import ResponseDefinitionInput, coerce_response_definition


def response_area(curve: ResponseDefinitionInput) -> float:
    """Return the integral of a sampled curve or realized band specification."""

    sampled_curve = _as_curve(curve)
    wavelength_nm = np.asarray(sampled_curve.wavelength_nm, dtype=float)
    response = np.asarray(sampled_curve.response, dtype=float)
    return _integrate(response, wavelength_nm)


def convolve_spectrum(
    spectrum_wavelength_nm: np.ndarray,
    spectrum_values: np.ndarray,
    response_definition: ResponseDefinitionInput,
) -> float:
    """Convolve a spectrum with a sampled curve, band spec, mapping, or callable."""

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
    if abs(denominator) < 1e-15:
        raise ValueError("response curve has zero area")
    return numerator / denominator


def convolution_weights(
    spectrum_wavelength_nm: np.ndarray,
    response_definition: ResponseDefinitionInput,
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
    if abs(total) < 1e-15:
        raise ValueError("response definition does not overlap the provided spectrum grid")
    return weights / total


def _as_curve(response_definition: ResponseDefinitionInput) -> SampledCurve:
    resolved_definition = coerce_response_definition(response_definition)
    if isinstance(resolved_definition, SampledCurve):
        return resolved_definition
    return realize_curve(resolved_definition)


def _integrate(values: np.ndarray, wavelength_nm: np.ndarray) -> float:
    trapezoid = getattr(np, "trapezoid", None)
    if trapezoid is None:
        trapezoid = getattr(np, "trapz", None)
    if trapezoid is None:
        raise RuntimeError("NumPy integration helper not available; expected trapezoid or trapz")
    return float(trapezoid(values, wavelength_nm))


def _interval_widths(wavelength_nm: np.ndarray) -> np.ndarray:
    widths = np.empty_like(wavelength_nm, dtype=float)
    widths[0] = (wavelength_nm[1] - wavelength_nm[0]) / 2.0
    widths[-1] = (wavelength_nm[-1] - wavelength_nm[-2]) / 2.0
    widths[1:-1] = (wavelength_nm[2:] - wavelength_nm[:-2]) / 2.0
    return widths
