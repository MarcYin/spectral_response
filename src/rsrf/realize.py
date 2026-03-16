"""Realization helpers for converting band specs into sampled curves."""

from __future__ import annotations

from dataclasses import replace
import math

import numpy as np

from .models import BandSpec, GridPolicy, SampledCurve


def sigma_from_fwhm(fwhm_nm: float) -> float:
    """Convert FWHM to Gaussian sigma."""

    if fwhm_nm <= 0:
        raise ValueError("fwhm_nm must be positive")
    return fwhm_nm / (2.0 * math.sqrt(2.0 * math.log(2.0)))


def adaptive_step_nm(
    fwhm_nm: float,
    *,
    samples_per_fwhm: int = 10,
    max_step_nm: float = 1.0,
    min_step_nm: float = 0.01,
) -> float:
    """Choose a sampling step for local curve realization."""

    if samples_per_fwhm <= 0:
        raise ValueError("samples_per_fwhm must be positive")
    candidate = fwhm_nm / float(samples_per_fwhm)
    return max(min_step_nm, min(candidate, max_step_nm))


def gaussian_curve_from_band_spec(
    band_spec: BandSpec,
    *,
    truncate_sigma: float = 4.0,
    samples_per_fwhm: int = 10,
    max_step_nm: float = 1.0,
    min_step_nm: float = 0.01,
) -> SampledCurve:
    """Realize a Gaussian curve from center wavelength and FWHM."""

    sigma_nm = sigma_from_fwhm(band_spec.fwhm_nm)
    step_nm = adaptive_step_nm(
        band_spec.fwhm_nm,
        samples_per_fwhm=samples_per_fwhm,
        max_step_nm=max_step_nm,
        min_step_nm=min_step_nm,
    )
    half_width_nm = truncate_sigma * sigma_nm
    half_steps = int(math.ceil(half_width_nm / step_nm))
    offsets_nm = np.arange(-half_steps, half_steps + 1, dtype=float) * step_nm
    wavelength_nm = band_spec.center_wavelength_nm + offsets_nm
    response = np.exp(
        -0.5 * ((wavelength_nm - band_spec.center_wavelength_nm) / sigma_nm) ** 2
    )
    return SampledCurve(
        band_id=band_spec.band_id,
        wavelength_nm=wavelength_nm,
        response=response,
        source_variant="gaussian_from_fwhm",
    )


def realize_curve(
    band_spec: BandSpec,
    *,
    profile_type: str = "gaussian",
    grid_policy: GridPolicy | None = None,
    normalization: str | None = "peak_1.0",
    source_variant: str | None = None,
) -> SampledCurve:
    """Realize a sampled curve from a band specification."""

    if profile_type != "gaussian":
        raise NotImplementedError(f"unsupported profile_type: {profile_type}")
    if normalization not in (None, "peak_1.0"):
        raise NotImplementedError(f"unsupported normalization: {normalization}")
    if grid_policy is not None and grid_policy.kind != "adaptive_per_band":
        raise NotImplementedError(f"unsupported grid policy: {grid_policy.kind}")

    curve = gaussian_curve_from_band_spec(
        band_spec,
        truncate_sigma=4.0 if grid_policy is None else grid_policy.truncate_sigma,
        samples_per_fwhm=10 if grid_policy is None else grid_policy.samples_per_fwhm,
        max_step_nm=1.0 if grid_policy is None else grid_policy.max_step_nm,
    )
    if source_variant is not None:
        return replace(curve, source_variant=source_variant)
    return curve


def estimate_center_wavelength(curve: SampledCurve) -> float:
    """Estimate the peak wavelength from a sampled curve."""

    wavelength_nm = np.asarray(curve.wavelength_nm, dtype=float)
    response = np.asarray(curve.response, dtype=float)
    peak_index = int(np.argmax(response))
    return float(wavelength_nm[peak_index])


def estimate_fwhm(curve: SampledCurve) -> float:
    """Estimate FWHM from a sampled curve by threshold crossing."""

    wavelength_nm = np.asarray(curve.wavelength_nm, dtype=float)
    response = np.asarray(curve.response, dtype=float)
    half_max = float(response.max()) / 2.0
    mask = response >= half_max
    if not np.any(mask):
        raise ValueError("curve does not contain a half-maximum support")
    return float(wavelength_nm[mask][-1] - wavelength_nm[mask][0])
