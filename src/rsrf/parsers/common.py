"""Shared helpers for sampled-curve parser implementations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from ..ingest import ParsedArtifacts
from ..io import artifact_file_count, artifact_sha256, artifact_size_bytes
from ..models import SourceManifest
from ..realize import estimate_center_wavelength, estimate_fwhm


@dataclass(frozen=True)
class ParsedBandCurve:
    """Intermediate band curve produced by a parser."""

    band_id: str
    wavelength_nm: Sequence[float]
    response: Sequence[float]
    band_index: int | None = None
    band_name: str | None = None
    band_status: str = "nominal"


@dataclass(frozen=True)
class NormalizedCurveSamples:
    """Normalized sampled-curve arrays plus normalization counters."""

    wavelength_nm: np.ndarray
    response: np.ndarray
    dropped_nonfinite_samples: int
    duplicate_wavelength_samples: int
    negative_values_clipped: int
    values_capped_to_one: int


def build_sampled_curve_artifacts(
    manifest: SourceManifest,
    source_artifact_path: Path,
    bands: Sequence[ParsedBandCurve],
    *,
    parser_module: str,
    parser_function: str,
    extra_metadata: Mapping[str, Any] | None = None,
) -> ParsedArtifacts:
    """Build canonical sampled-curve artifacts from per-band arrays."""

    if not bands:
        raise ValueError("parser did not produce any band curves")

    curve_rows: list[dict[str, Any]] = []
    band_rows: list[dict[str, Any]] = []
    band_metrics: dict[str, dict[str, Any]] = {}
    global_wavelength_min_nm: float | None = None
    global_wavelength_max_nm: float | None = None
    total_dropped_nonfinite_samples = 0
    total_duplicate_wavelength_samples = 0
    total_negative_values_clipped = 0
    total_values_capped_to_one = 0

    for order_index, band in enumerate(bands, start=1):
        wavelength_nm = np.asarray(band.wavelength_nm, dtype=float)
        response = np.asarray(band.response, dtype=float)
        if wavelength_nm.size == 0:
            raise ValueError(f"{band.band_id} does not contain any wavelength samples")
        if wavelength_nm.shape != response.shape:
            raise ValueError(f"{band.band_id} wavelength/response arrays must have the same shape")

        normalized = _normalize_curve_samples(wavelength_nm, response)
        wavelength_nm = normalized.wavelength_nm
        response = normalized.response
        total_dropped_nonfinite_samples += normalized.dropped_nonfinite_samples
        total_duplicate_wavelength_samples += normalized.duplicate_wavelength_samples
        total_negative_values_clipped += normalized.negative_values_clipped
        total_values_capped_to_one += normalized.values_capped_to_one

        global_wavelength_min_nm = float(wavelength_nm.min()) if global_wavelength_min_nm is None else min(
            global_wavelength_min_nm, float(wavelength_nm.min())
        )
        global_wavelength_max_nm = float(wavelength_nm.max()) if global_wavelength_max_nm is None else max(
            global_wavelength_max_nm, float(wavelength_nm.max())
        )

        native_sampling_nm = _infer_native_sampling_nm(wavelength_nm)
        support_min_nm, support_max_nm = _infer_support_bounds(wavelength_nm, response)
        sample_curve = _curve_object(band.band_id, wavelength_nm, response, manifest.representation_variant)

        for wavelength_value, response_value in zip(wavelength_nm.tolist(), response.tolist()):
            curve_rows.append(
                {
                    "sensor_unit_id": manifest.sensor_unit_id,
                    "representation_variant": manifest.representation_variant,
                    "band_id": band.band_id,
                    "wavelength_nm": float(wavelength_value),
                    "response": float(response_value),
                    "curve_origin": "canonical_sampled",
                    "realization_id": None,
                    "is_native": True,
                    "is_trimmed": False,
                    "source_id": manifest.source_id,
                }
            )

        band_index = band.band_index if band.band_index is not None else order_index
        center_wavelength_nm = estimate_center_wavelength(sample_curve)
        fwhm_nm = estimate_fwhm(sample_curve)
        band_name = band.band_name or band.band_id
        band_rows.append(
            {
                "sensor_unit_id": manifest.sensor_unit_id,
                "representation_variant": manifest.representation_variant,
                "band_id": band.band_id,
                "band_index": band_index,
                "band_name": band_name,
                "center_wavelength_nm": center_wavelength_nm,
                "fwhm_nm": fwhm_nm,
                "published_shape_type": manifest.canonical.published_shape_type,
                "band_status": band.band_status,
                "native_support_min_nm": support_min_nm,
                "native_support_max_nm": support_max_nm,
                "native_sampling_nm": native_sampling_nm,
                "normalization": manifest.canonical.normalization,
                "has_sampled_curve": True,
                "has_band_spec": False,
            }
        )
        band_metrics[band.band_id] = {
            "band_index": band_index,
            "center_wavelength_nm": center_wavelength_nm,
            "fwhm_nm": fwhm_nm,
            "native_support_min_nm": support_min_nm,
            "native_support_max_nm": support_max_nm,
            "native_sampling_nm": native_sampling_nm,
            "sample_count": int(wavelength_nm.size),
            "normalization": {
                "dropped_nonfinite_samples": normalized.dropped_nonfinite_samples,
                "duplicate_wavelength_samples": normalized.duplicate_wavelength_samples,
                "negative_values_clipped": normalized.negative_values_clipped,
                "values_capped_to_one": normalized.values_capped_to_one,
            },
        }

    metadata: dict[str, Any] = {
        "source_id": manifest.source_id,
        "sensor_unit_id": manifest.sensor_unit_id,
        "representation_variant": manifest.representation_variant,
        "content_kind": manifest.content_kind.value,
        "source_tier": manifest.source_tier.value,
        "source_type": manifest.source_type.value,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "parser": {
            "module": parser_module,
            "function": parser_function,
            "script": manifest.parser.script,
            "entrypoint": manifest.parser.entrypoint,
        },
        "source_artifact": {
            "path": str(source_artifact_path),
            "sha256": artifact_sha256(source_artifact_path),
            "size_bytes": artifact_size_bytes(source_artifact_path),
            "file_count": artifact_file_count(source_artifact_path),
        },
        "curve_table": {
            "row_count": len(curve_rows),
            "band_count": len(band_rows),
            "wavelength_min_nm": global_wavelength_min_nm,
            "wavelength_max_nm": global_wavelength_max_nm,
        },
        "curve_normalization": {
            "dropped_nonfinite_samples": total_dropped_nonfinite_samples,
            "duplicate_wavelength_samples": total_duplicate_wavelength_samples,
            "negative_values_clipped": total_negative_values_clipped,
            "values_capped_to_one": total_values_capped_to_one,
        },
        "band_metrics": band_metrics,
        "manifest": manifest.to_dict(),
    }
    if extra_metadata:
        metadata.update(dict(extra_metadata))

    return ParsedArtifacts(
        curve_rows=curve_rows,
        band_rows=band_rows,
        metadata=metadata,
    )


def _curve_object(band_id: str, wavelength_nm: np.ndarray, response: np.ndarray, variant: str):
    from ..models import SampledCurve

    return SampledCurve(
        band_id=band_id,
        wavelength_nm=wavelength_nm,
        response=response,
        source_variant=variant,
    )


def _normalize_curve_samples(
    wavelength_nm: np.ndarray,
    response: np.ndarray,
) -> NormalizedCurveSamples:
    finite_mask = np.isfinite(wavelength_nm) & np.isfinite(response)
    dropped_nonfinite_samples = int(wavelength_nm.size - int(np.count_nonzero(finite_mask)))
    if not np.any(finite_mask):
        raise ValueError("curve samples do not contain any finite wavelength/response pairs")

    wavelength_nm = wavelength_nm[finite_mask]
    response = response[finite_mask]

    sort_index = np.argsort(wavelength_nm, kind="mergesort")
    wavelength_nm = wavelength_nm[sort_index]
    response = response[sort_index]

    negative_mask = response < 0.0
    negative_values_clipped = int(np.count_nonzero(negative_mask))
    if negative_values_clipped:
        response = response.copy()
        response[negative_mask] = 0.0

    overbound_mask = response > 1.0
    values_capped_to_one = int(np.count_nonzero(overbound_mask))
    if values_capped_to_one:
        if response.base is None:
            response = response.copy()
        response[overbound_mask] = 1.0

    duplicate_wavelength_samples = int(wavelength_nm.size - np.unique(wavelength_nm).size)
    if duplicate_wavelength_samples:
        unique_wavelength_nm, inverse = np.unique(wavelength_nm, return_inverse=True)
        deduplicated_response = np.full(unique_wavelength_nm.shape, -np.inf, dtype=float)
        np.maximum.at(deduplicated_response, inverse, response)
        wavelength_nm = unique_wavelength_nm
        response = deduplicated_response

    return NormalizedCurveSamples(
        wavelength_nm=wavelength_nm,
        response=response,
        dropped_nonfinite_samples=dropped_nonfinite_samples,
        duplicate_wavelength_samples=duplicate_wavelength_samples,
        negative_values_clipped=negative_values_clipped,
        values_capped_to_one=values_capped_to_one,
    )


def _infer_native_sampling_nm(wavelength_nm: np.ndarray) -> float | None:
    if wavelength_nm.size < 2:
        return None
    steps = np.diff(wavelength_nm)
    if np.allclose(steps, steps[0], rtol=1e-6, atol=1e-9):
        return float(steps[0])
    return None


def _infer_support_bounds(
    wavelength_nm: np.ndarray,
    response: np.ndarray,
) -> tuple[float, float]:
    positive_mask = response > 0.0
    if np.any(positive_mask):
        return float(wavelength_nm[positive_mask][0]), float(wavelength_nm[positive_mask][-1])
    return float(wavelength_nm[0]), float(wavelength_nm[-1])
