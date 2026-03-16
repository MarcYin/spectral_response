"""Helpers for metadata-only band specifications."""

from __future__ import annotations

from .models import BandSpec


def default_band_id(band_index: int) -> str:
    """Build a stable band identifier for unnamed hyperspectral bands."""

    if band_index < 0:
        raise ValueError("band_index must be non-negative")
    return f"B{band_index:03d}"


def build_band_spec(
    center_wavelength_nm: float,
    fwhm_nm: float,
    *,
    band_index: int | None = None,
    band_id: str | None = None,
    band_name: str | None = None,
    band_status: str = "nominal",
    published_shape_type: str = "unknown",
) -> BandSpec:
    """Create a bootstrap band specification."""

    if center_wavelength_nm <= 0:
        raise ValueError("center_wavelength_nm must be positive")
    if fwhm_nm <= 0:
        raise ValueError("fwhm_nm must be positive")

    resolved_band_id = band_id
    if resolved_band_id is None:
        if band_index is None:
            raise ValueError("band_id or band_index must be provided")
        resolved_band_id = default_band_id(band_index)

    return BandSpec(
        band_id=resolved_band_id,
        center_wavelength_nm=center_wavelength_nm,
        fwhm_nm=fwhm_nm,
        band_index=band_index,
        band_name=band_name,
        band_status=band_status,
        published_shape_type=published_shape_type,
    )
