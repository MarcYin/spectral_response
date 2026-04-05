"""Helpers for coercing runtime response-definition inputs."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any, Union

import numpy as np

from .models import BandSpec, SampledCurve

ResponseDefinition = Union[SampledCurve, BandSpec]
ResponseDefinitionInput = Union[ResponseDefinition, Mapping[str, Any], Callable[[], object]]

_SAMPLED_KINDS = {"sampled", "sampled_curve"}
_BAND_SPEC_KINDS = {"gaussian", "band_spec"}

_WAVELENGTH_KEYS = ("wavelength_nm", "wavelength")
_RESPONSE_KEYS = ("response", "relative_spectral_response", "spectral_response", "relative_response", "rsr")
_CENTER_KEYS = ("center_wavelength_nm", "center_wavelength")
_FWHM_KEYS = ("fwhm_nm", "fwhm")
_MISSING = object()


def coerce_response_definition(
    response_definition: ResponseDefinitionInput,
    *,
    band_id: str = "custom",
    source_variant: str | None = "custom",
) -> ResponseDefinition:
    """Normalize user-provided response-definition inputs.

    Accepted inputs are:

    - a ``SampledCurve`` or ``BandSpec``
    - a mapping with ``wavelength_nm`` and ``response``
    - a mapping with ``center_wavelength_nm`` and ``fwhm_nm``
    - a zero-argument callable returning any accepted input form
    """

    if callable(response_definition):
        resolved = response_definition()
        return coerce_response_definition(
            resolved,
            band_id=band_id,
            source_variant=source_variant,
        )

    if isinstance(response_definition, SampledCurve):
        _validate_sampled_curve(response_definition)
        return response_definition

    if isinstance(response_definition, BandSpec):
        _validate_band_spec(response_definition)
        return response_definition

    if isinstance(response_definition, Mapping):
        return _coerce_mapping(
            response_definition,
            band_id=band_id,
            source_variant=source_variant,
        )

    raise TypeError("response_definition must be a SampledCurve, BandSpec, mapping, or zero-argument callable")


def validate_response_definition(
    response_definition: ResponseDefinitionInput,
    *,
    band_id: str = "custom",
    source_variant: str | None = "custom",
) -> ResponseDefinition:
    """Validate and normalize any supported response-definition input."""

    return coerce_response_definition(
        response_definition,
        band_id=band_id,
        source_variant=source_variant,
    )


def response_definition_to_dict(
    response_definition: ResponseDefinitionInput,
    *,
    band_id: str = "custom",
    source_variant: str | None = "custom",
) -> dict[str, Any]:
    """Normalize a response definition into the stable JSON-facing shape."""

    normalized = coerce_response_definition(
        response_definition,
        band_id=band_id,
        source_variant=source_variant,
    )

    if isinstance(normalized, SampledCurve):
        return {
            "kind": "sampled",
            "wavelength_nm": np.asarray(normalized.wavelength_nm, dtype=float).tolist(),
            "response": np.asarray(normalized.response, dtype=float).tolist(),
        }

    return {
        "kind": "band_spec",
        "center_wavelength_nm": float(normalized.center_wavelength_nm),
        "fwhm_nm": float(normalized.fwhm_nm),
    }


def _coerce_mapping(
    response_definition: Mapping[str, Any],
    *,
    band_id: str,
    source_variant: str | None,
) -> ResponseDefinition:
    wavelength_nm = _mapping_value(response_definition, _WAVELENGTH_KEYS)
    response = _mapping_value(response_definition, _RESPONSE_KEYS)
    center_wavelength_nm = _mapping_value(response_definition, _CENTER_KEYS)
    fwhm_nm = _mapping_value(response_definition, _FWHM_KEYS)
    kind = _normalized_kind(response_definition.get("kind"))

    has_sampled_keys = wavelength_nm is not _MISSING or response is not _MISSING
    has_band_spec_keys = center_wavelength_nm is not _MISSING or fwhm_nm is not _MISSING

    if kind in _SAMPLED_KINDS:
        if has_band_spec_keys:
            raise ValueError("sampled response_definition mappings cannot also include center_wavelength_nm or fwhm_nm")
        has_sampled_keys = True
    elif kind in _BAND_SPEC_KINDS:
        if has_sampled_keys:
            raise ValueError("gaussian response_definition mappings cannot also include wavelength_nm or response")
        has_band_spec_keys = True
    elif kind is not None:
        raise ValueError(f"unsupported response_definition kind: {kind}")

    if has_sampled_keys and has_band_spec_keys:
        raise ValueError(
            "response_definition mapping must describe either sampled points or center_wavelength_nm + fwhm_nm"
        )

    if has_sampled_keys:
        if wavelength_nm is _MISSING or response is _MISSING:
            raise ValueError(
                "sampled-curve mappings require both wavelength_nm and response "
                "(aliases: wavelength, relative_spectral_response, spectral_response, rsr)"
            )
        curve = SampledCurve(
            band_id=str(response_definition.get("band_id", band_id)),
            wavelength_nm=wavelength_nm,
            response=response,
            source_variant=_optional_string(response_definition.get("source_variant", source_variant)),
        )
        _validate_sampled_curve(curve)
        return curve

    if has_band_spec_keys:
        if center_wavelength_nm is _MISSING or fwhm_nm is _MISSING:
            raise ValueError(
                "band-spec mappings require both center_wavelength_nm and fwhm_nm (aliases: center_wavelength, fwhm)"
            )
        shape_param_json = response_definition.get("shape_param_json", {})
        if not isinstance(shape_param_json, Mapping):
            raise ValueError("shape_param_json must be a mapping when provided")
        band_index = response_definition.get("band_index")
        spec = BandSpec(
            band_id=str(response_definition.get("band_id", band_id)),
            center_wavelength_nm=float(center_wavelength_nm),
            fwhm_nm=float(fwhm_nm),
            band_index=None if band_index is None else int(band_index),
            band_name=_optional_string(response_definition.get("band_name")),
            band_status=str(response_definition.get("band_status", "nominal")),
            published_shape_type=str(response_definition.get("published_shape_type", "unknown")),
            shape_param_json=dict(shape_param_json),
        )
        _validate_band_spec(spec)
        return spec

    raise ValueError(
        "response_definition mapping must include either wavelength_nm + response or center_wavelength_nm + fwhm_nm"
    )


def _validate_sampled_curve(curve: SampledCurve) -> None:
    wavelength_nm = np.asarray(curve.wavelength_nm, dtype=float)
    response = np.asarray(curve.response, dtype=float)

    if wavelength_nm.ndim != 1 or response.ndim != 1:
        raise ValueError("sampled curves require one-dimensional wavelength_nm and response arrays")
    if wavelength_nm.size < 2:
        raise ValueError("sampled curves require at least two wavelength samples")
    if wavelength_nm.size != response.size:
        raise ValueError("wavelength_nm and response must have the same length")
    if not np.all(np.isfinite(wavelength_nm)):
        raise ValueError("wavelength_nm must contain only finite values")
    if not np.all(np.diff(wavelength_nm) > 0):
        raise ValueError("wavelength_nm must be strictly increasing")
    if not np.all(np.isfinite(response)):
        raise ValueError("response must contain only finite values")
    if np.any(response < 0):
        raise ValueError("response must be non-negative")
    if float(response.max()) <= 0.0:
        raise ValueError("response must contain at least one positive value")


def _validate_band_spec(band_spec: BandSpec) -> None:
    if not np.isfinite(float(band_spec.center_wavelength_nm)):
        raise ValueError("center_wavelength_nm must be finite")
    if float(band_spec.center_wavelength_nm) <= 0.0:
        raise ValueError("center_wavelength_nm must be positive")
    if not np.isfinite(float(band_spec.fwhm_nm)):
        raise ValueError("fwhm_nm must be finite")
    if float(band_spec.fwhm_nm) <= 0.0:
        raise ValueError("fwhm_nm must be positive")


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _mapping_value(payload: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in payload:
            return payload[key]
    return _MISSING


def _normalized_kind(value: object) -> str | None:
    if value is None:
        return None
    return str(value).strip().lower()
