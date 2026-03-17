"""Shared rendering helpers for CLI command output."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Sequence

from ..convolve import response_area
from ..models import BandSpec, SampledCurve


def normalize_json_value(value: Any) -> Any:
    """Normalize values into JSON-safe plain Python objects."""

    if isinstance(value, dict):
        return {str(key): normalize_json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [normalize_json_value(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "item") and callable(value.item):
        return normalize_json_value(value.item())
    if value is None:
        return None
    if isinstance(value, float) and value != value:
        return None
    return value


def print_json(payload: Any) -> int:
    """Print a JSON payload with stable formatting."""

    normalized = normalize_json_value(payload)
    print(json.dumps(normalized, indent=2, sort_keys=True, allow_nan=False))
    return 0


def exception_message(exc: Exception) -> str:
    """Extract a user-facing message from an exception."""

    if exc.args:
        return str(exc.args[0])
    return str(exc)


def print_manifest_errors(manifest_path: Path, errors: Sequence[str]) -> int:
    """Print manifest-validation failures in CLI form."""

    print(f"Manifest validation failed for {manifest_path}:")
    for error in errors:
        print(f"- {error}")
    return 1


def summarize_response_definition(
    sensor_unit_id: str,
    representation_variant: str,
    response_definition: SampledCurve | BandSpec,
) -> dict[str, Any]:
    """Return a compact JSON summary for a response definition."""

    if isinstance(response_definition, SampledCurve):
        return {
            "content_kind": "sampled_curve",
            "sensor_unit_id": sensor_unit_id,
            "representation_variant": representation_variant,
            "band_id": response_definition.band_id,
            "source_variant": response_definition.source_variant,
            "sample_count": len(response_definition.wavelength_nm),
            "wavelength_min_nm": float(min(response_definition.wavelength_nm)),
            "wavelength_max_nm": float(max(response_definition.wavelength_nm)),
            "peak_response": float(max(response_definition.response)),
            "area": response_area(response_definition),
        }
    return {
        "content_kind": "band_spec",
        "sensor_unit_id": sensor_unit_id,
        "representation_variant": representation_variant,
        "band_id": response_definition.band_id,
        "band_index": response_definition.band_index,
        "band_name": response_definition.band_name,
        "band_status": response_definition.band_status,
        "center_wavelength_nm": response_definition.center_wavelength_nm,
        "fwhm_nm": response_definition.fwhm_nm,
        "published_shape_type": response_definition.published_shape_type,
        "shape_param_json": dict(response_definition.shape_param_json),
    }
