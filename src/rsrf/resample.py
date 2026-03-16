"""Resampling helpers for sampled response curves."""

from __future__ import annotations

import numpy as np

from .models import SampledCurve


def resample_curve(curve: SampledCurve, target_grid_nm: np.ndarray) -> SampledCurve:
    """Resample a curve onto a target wavelength grid using linear interpolation."""

    source_wavelength_nm = np.asarray(curve.wavelength_nm, dtype=float)
    source_response = np.asarray(curve.response, dtype=float)
    target_grid_nm = np.asarray(target_grid_nm, dtype=float)
    target_response = np.interp(
        target_grid_nm,
        source_wavelength_nm,
        source_response,
        left=0.0,
        right=0.0,
    )
    return SampledCurve(
        band_id=curve.band_id,
        wavelength_nm=target_grid_nm,
        response=target_response,
        source_variant=curve.source_variant,
    )
