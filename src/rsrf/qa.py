"""Validation helpers for canonical and realized sensor representations."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import numpy as np

from .api import get_metadata, list_bands, load_band_spec, load_curve
from .convolve import response_area
from .io import write_json
from .models import BandSpec, ContentKind, GridPolicy, SampledCurve
from .plotting import plot_band_spec_summary, plot_curve_collection, plot_curve_overlays
from .realize import estimate_center_wavelength, estimate_fwhm, realize_curve
from .registry import build_repo_layout

OVERLAY_REFERENCE_FILENAME = "overlay_reference.csv"
OVERLAY_MAX_ABS_TOLERANCE = 0.02


def validate_sensor(
    sensor_unit_id: str,
    representation_variant: str | None = None,
    *,
    root: Path | None = None,
) -> dict[str, Any]:
    """Validate a sensor representation and return a structured report."""

    metadata = get_metadata(sensor_unit_id, representation_variant, root=root)
    resolved_variant = str(metadata["representation_variant"])
    content_kind = ContentKind(str(metadata["content_kind"]))

    if content_kind == ContentKind.SAMPLED_CURVE:
        return validate_sampled_curve_variant(
            sensor_unit_id,
            resolved_variant,
            root=root,
        )
    if content_kind == ContentKind.BAND_SPEC:
        return validate_band_spec_variant(
            sensor_unit_id,
            resolved_variant,
            root=root,
        )
    raise NotImplementedError(f"validation not implemented for content_kind={content_kind.value}")


def validate_sampled_curve_variant(
    sensor_unit_id: str,
    representation_variant: str,
    *,
    root: Path | None = None,
) -> dict[str, Any]:
    """Validate a sampled-curve representation."""

    metadata = get_metadata(sensor_unit_id, representation_variant, root=root)
    band_rows = list_bands(sensor_unit_id, representation_variant, root=root)
    failures: list[dict[str, Any]] = []
    band_metrics: dict[str, dict[str, Any]] = {}
    expected_band_count = _expected_band_count(metadata)

    if expected_band_count is not None and len(band_rows) != expected_band_count:
        failures.append(
            _failure(
                sensor_unit_id,
                representation_variant,
                None,
                "expected_band_count",
                f"expected {expected_band_count} bands but found {len(band_rows)}",
            )
        )

    for band_row in band_rows:
        band_id = str(band_row["band_id"])
        curve = load_curve(sensor_unit_id, band_id, representation_variant, root=root)
        wavelength_nm = np.asarray(curve.wavelength_nm, dtype=float)
        response = np.asarray(curve.response, dtype=float)
        duplicate_samples = int(wavelength_nm.size - np.unique(wavelength_nm).size)
        strictly_increasing = bool(wavelength_nm.size > 1 and np.all(np.diff(wavelength_nm) > 0))
        finite_values = bool(np.all(np.isfinite(wavelength_nm)) and np.all(np.isfinite(response)))
        nonnegative_response = bool(np.all(response >= 0.0))
        positive_peak = bool(float(response.max()) > 0.0)

        if not strictly_increasing:
            failures.append(
                _failure(
                    sensor_unit_id,
                    representation_variant,
                    band_id,
                    "strictly_increasing_wavelength",
                    "wavelength grid must be strictly increasing",
                )
            )
        if duplicate_samples > 0:
            failures.append(
                _failure(
                    sensor_unit_id,
                    representation_variant,
                    band_id,
                    "duplicate_wavelength_samples",
                    f"found {duplicate_samples} duplicate wavelength samples",
                )
            )
        if not finite_values:
            failures.append(
                _failure(
                    sensor_unit_id,
                    representation_variant,
                    band_id,
                    "finite_values",
                    "wavelength and response arrays must be finite",
                )
            )
        if not nonnegative_response:
            failures.append(
                _failure(
                    sensor_unit_id,
                    representation_variant,
                    band_id,
                    "nonnegative_response",
                    "response values must be non-negative",
                )
            )
        if not positive_peak:
            failures.append(
                _failure(
                    sensor_unit_id,
                    representation_variant,
                    band_id,
                    "positive_peak",
                    "response curve must have a positive peak",
                )
            )

        band_metrics[band_id] = {
            "sample_count": int(wavelength_nm.size),
            "wavelength_min_nm": float(wavelength_nm.min()),
            "wavelength_max_nm": float(wavelength_nm.max()),
            "peak_response": float(response.max()),
            "area": response_area(curve),
        }

    overlay_checks = _validate_sampled_curve_overlay(
        sensor_unit_id,
        representation_variant,
        metadata,
        failures,
        root=root,
    )

    report = {
        "sensor_unit_id": sensor_unit_id,
        "representation_variant": representation_variant,
        "content_kind": ContentKind.SAMPLED_CURVE.value,
        "passed": not failures,
        "failure_count": len(failures),
        "failures": failures,
        "summary": {
            "band_count": len(band_rows),
            "expected_band_count": expected_band_count,
        },
        "band_metrics": band_metrics,
        "overlay_checks": overlay_checks,
        "metadata_generated_at": metadata.get("generated_at"),
    }
    return report


def validate_band_spec_variant(
    sensor_unit_id: str,
    representation_variant: str,
    *,
    root: Path | None = None,
) -> dict[str, Any]:
    """Validate a band-spec representation and its realization recipe."""

    metadata = get_metadata(sensor_unit_id, representation_variant, root=root)
    band_rows = list_bands(sensor_unit_id, representation_variant, root=root)
    failures: list[dict[str, Any]] = []
    band_specs: list[BandSpec] = [
        load_band_spec(sensor_unit_id, str(band_row["band_id"]), representation_variant, root=root)
        for band_row in band_rows
    ]
    expected_band_count = _expected_band_count(metadata)
    if expected_band_count is not None and len(band_specs) != expected_band_count:
        failures.append(
            _failure(
                sensor_unit_id,
                representation_variant,
                None,
                "expected_band_count",
                f"expected {expected_band_count} bands but found {len(band_specs)}",
            )
        )

    band_indices = [band_spec.band_index for band_spec in band_specs if band_spec.band_index is not None]
    duplicate_indices = _duplicate_values(band_indices)
    if duplicate_indices:
        for duplicate_index in sorted(duplicate_indices):
            failures.append(
                _failure(
                    sensor_unit_id,
                    representation_variant,
                    None,
                    "duplicate_band_index",
                    f"duplicate band_index detected: {duplicate_index}",
                )
            )

    centers = np.asarray([band_spec.center_wavelength_nm for band_spec in band_specs], dtype=float)
    centers_monotonic = bool(len(centers) < 2 or np.all(np.diff(centers) > 0))
    if metadata["manifest"]["validation"]["monotonic_centers_required"] and not centers_monotonic:
        failures.append(
            _failure(
                sensor_unit_id,
                representation_variant,
                None,
                "monotonic_centers",
                "center wavelengths must be strictly increasing",
            )
        )

    band_metrics: dict[str, dict[str, Any]] = {}
    realizable_band_specs: list[BandSpec] = []
    for band_spec in band_specs:
        finite_center = bool(np.isfinite(band_spec.center_wavelength_nm))
        finite_fwhm = bool(np.isfinite(band_spec.fwhm_nm))
        positive_center = finite_center and band_spec.center_wavelength_nm > 0
        positive_fwhm = finite_fwhm and band_spec.fwhm_nm > 0

        if not finite_center:
            failures.append(
                _failure(
                    sensor_unit_id,
                    representation_variant,
                    band_spec.band_id,
                    "finite_center_wavelength",
                    "center_wavelength_nm must be finite",
                )
            )
        if not positive_center:
            failures.append(
                _failure(
                    sensor_unit_id,
                    representation_variant,
                    band_spec.band_id,
                    "positive_center_wavelength",
                    "center_wavelength_nm must be positive",
                )
            )
        if not finite_fwhm:
            failures.append(
                _failure(
                    sensor_unit_id,
                    representation_variant,
                    band_spec.band_id,
                    "finite_fwhm",
                    "fwhm_nm must be finite",
                )
            )
        if not positive_fwhm:
            failures.append(
                _failure(
                    sensor_unit_id,
                    representation_variant,
                    band_spec.band_id,
                    "positive_fwhm",
                    "fwhm_nm must be positive",
                )
            )
        if positive_center and positive_fwhm:
            realizable_band_specs.append(band_spec)
        band_metrics[band_spec.band_id] = {
            "band_index": band_spec.band_index,
            "center_wavelength_nm": band_spec.center_wavelength_nm,
            "fwhm_nm": band_spec.fwhm_nm,
            "band_status": band_spec.band_status,
        }

    realization_checks = _validate_band_spec_realization(
        sensor_unit_id,
        representation_variant,
        metadata,
        realizable_band_specs,
        failures,
    )

    report = {
        "sensor_unit_id": sensor_unit_id,
        "representation_variant": representation_variant,
        "content_kind": ContentKind.BAND_SPEC.value,
        "passed": not failures,
        "failure_count": len(failures),
        "failures": failures,
        "summary": {
            "band_count": len(band_specs),
            "expected_band_count": expected_band_count,
            "monotonic_centers": centers_monotonic,
        },
        "band_metrics": band_metrics,
        "realization_checks": realization_checks,
        "metadata_generated_at": metadata.get("generated_at"),
    }
    return report


def write_validation_artifacts(
    sensor_unit_id: str,
    representation_variant: str | None = None,
    *,
    root: Path | None = None,
    output_dir: Path | None = None,
) -> dict[str, Path]:
    """Write a validation report and overview plot for a sensor representation."""

    report = validate_sensor(sensor_unit_id, representation_variant, root=root)
    resolved_variant = str(report["representation_variant"])
    destination = output_dir
    if destination is None:
        layout = build_repo_layout(root)
        destination = layout.sensor_notes_root / sensor_unit_id / resolved_variant

    report_path = write_json(destination / "validation_report.json", report)
    plot_path = destination / "overview.png"

    if report["content_kind"] == ContentKind.SAMPLED_CURVE.value:
        curves = [
            load_curve(sensor_unit_id, str(band_row["band_id"]), resolved_variant, root=root)
            for band_row in list_bands(sensor_unit_id, resolved_variant, root=root)
        ]
        plot_curve_collection(
            curves,
            output_path=plot_path,
            title=f"{sensor_unit_id} / {resolved_variant}",
        )
        overlay_checks = report.get("overlay_checks", {})
        if overlay_checks.get("available"):
            overlay_curve_pairs = _load_overlay_curve_pairs(
                sensor_unit_id,
                resolved_variant,
                root=root,
            )
            if overlay_curve_pairs:
                overlay_path = destination / "overlay.png"
                plot_curve_overlays(
                    overlay_curve_pairs,
                    output_path=overlay_path,
                    title=f"{sensor_unit_id} / {resolved_variant} overlay",
                )
            else:
                overlay_path = None
        else:
            overlay_path = None
    else:
        band_specs = [
            load_band_spec(sensor_unit_id, str(band_row["band_id"]), resolved_variant, root=root)
            for band_row in list_bands(sensor_unit_id, resolved_variant, root=root)
        ]
        plot_band_spec_summary(
            band_specs,
            output_path=plot_path,
            title=f"{sensor_unit_id} / {resolved_variant}",
        )
        overlay_path = None

    written = {
        "report": report_path,
        "plot": plot_path,
    }
    if overlay_path is not None:
        written["overlay_plot"] = overlay_path
    return written


def _validate_band_spec_realization(
    sensor_unit_id: str,
    representation_variant: str,
    metadata: dict[str, Any],
    band_specs: list[BandSpec],
    failures: list[dict[str, Any]],
) -> dict[str, Any]:
    realization_section = metadata.get("realization")
    if not isinstance(realization_section, dict) or not realization_section.get("enabled"):
        return {"enabled": False}

    grid_policy_payload = realization_section.get("grid_policy")
    try:
        grid_policy = (
            None if grid_policy_payload is None else GridPolicy.from_dict(grid_policy_payload)
        )
    except Exception as exc:
        failures.append(
            _failure(
                sensor_unit_id,
                representation_variant,
                None,
                "realization_recipe",
                str(exc),
            )
        )
        return {
            "enabled": True,
            "output_representation_variant": realization_section.get("output_representation_variant"),
            "profile_type": realization_section.get("profile_type"),
            "error": str(exc),
            "per_band": {},
        }
    center_tolerance_nm = 1.0 if grid_policy is None else float(grid_policy.max_step_nm)
    fwhm_tolerance_nm = 2.0 if grid_policy is None else max(float(grid_policy.max_step_nm) * 2.0, 1.0)

    per_band: dict[str, dict[str, Any]] = {}
    max_center_error = 0.0
    max_fwhm_error = 0.0
    for band_spec in band_specs:
        try:
            curve = realize_curve(
                band_spec,
                profile_type=str(realization_section.get("profile_type") or "gaussian"),
                grid_policy=grid_policy,
                normalization=realization_section.get("normalization"),
                source_variant=realization_section.get("output_representation_variant"),
            )
            center_error = abs(estimate_center_wavelength(curve) - band_spec.center_wavelength_nm)
            fwhm_error = abs(estimate_fwhm(curve) - band_spec.fwhm_nm)
        except Exception as exc:
            failures.append(
                _failure(
                    sensor_unit_id,
                    representation_variant,
                    band_spec.band_id,
                    "realization_recipe",
                    str(exc),
                )
            )
            per_band[band_spec.band_id] = {
                "error": str(exc),
            }
            continue
        max_center_error = max(max_center_error, center_error)
        max_fwhm_error = max(max_fwhm_error, fwhm_error)
        if center_error > center_tolerance_nm:
            failures.append(
                _failure(
                    sensor_unit_id,
                    representation_variant,
                    band_spec.band_id,
                    "realized_center_tolerance",
                    f"realized center error {center_error:.3f} nm exceeds tolerance {center_tolerance_nm:.3f} nm",
                )
            )
        if fwhm_error > fwhm_tolerance_nm:
            failures.append(
                _failure(
                    sensor_unit_id,
                    representation_variant,
                    band_spec.band_id,
                    "realized_fwhm_tolerance",
                    f"realized FWHM error {fwhm_error:.3f} nm exceeds tolerance {fwhm_tolerance_nm:.3f} nm",
                )
            )
        per_band[band_spec.band_id] = {
            "center_abs_error_nm": center_error,
            "fwhm_abs_error_nm": fwhm_error,
        }

    return {
        "enabled": True,
        "output_representation_variant": realization_section.get("output_representation_variant"),
        "profile_type": realization_section.get("profile_type"),
        "center_tolerance_nm": center_tolerance_nm,
        "fwhm_tolerance_nm": fwhm_tolerance_nm,
        "max_center_abs_error_nm": max_center_error,
        "max_fwhm_abs_error_nm": max_fwhm_error,
        "per_band": per_band,
    }


def _validate_sampled_curve_overlay(
    sensor_unit_id: str,
    representation_variant: str,
    metadata: dict[str, Any],
    failures: list[dict[str, Any]],
    *,
    root: Path | None,
) -> dict[str, Any]:
    required = bool(metadata.get("manifest", {}).get("validation", {}).get("plot_overlay_required"))
    reference_path = _overlay_reference_path(sensor_unit_id, representation_variant, root=root)
    if not reference_path.exists():
        if required:
            failures.append(
                _failure(
                    sensor_unit_id,
                    representation_variant,
                    None,
                    "overlay_reference_missing",
                    f"overlay reference file not found: {reference_path}",
                )
            )
        return {
            "required": required,
            "available": False,
            "reference_path": str(reference_path),
            "band_count": 0,
        }

    reference_curves = _load_overlay_reference_curves(reference_path)
    if not reference_curves:
        failures.append(
            _failure(
                sensor_unit_id,
                representation_variant,
                None,
                "overlay_reference_empty",
                f"overlay reference file is empty: {reference_path}",
            )
        )
        return {
            "required": required,
            "available": False,
            "reference_path": str(reference_path),
            "band_count": 0,
        }

    per_band: dict[str, dict[str, Any]] = {}
    max_abs_diff = 0.0
    rmse_max = 0.0
    for band_id, reference_curve in reference_curves.items():
        try:
            curve = load_curve(sensor_unit_id, band_id, representation_variant, root=root)
        except KeyError as exc:
            failures.append(
                _failure(
                    sensor_unit_id,
                    representation_variant,
                    band_id,
                    "overlay_reference_band_missing",
                    str(exc),
                )
            )
            per_band[band_id] = {"error": str(exc)}
            continue
        reference_wavelength_nm = np.asarray(reference_curve.wavelength_nm, dtype=float)
        reference_response = np.asarray(reference_curve.response, dtype=float)
        curve_wavelength_nm = np.asarray(curve.wavelength_nm, dtype=float)
        curve_response = np.asarray(curve.response, dtype=float)
        sampled_response = np.interp(
            reference_wavelength_nm,
            curve_wavelength_nm,
            curve_response,
            left=np.nan,
            right=np.nan,
        )
        overlap_mask = np.isfinite(sampled_response)
        if not np.any(overlap_mask):
            failures.append(
                _failure(
                    sensor_unit_id,
                    representation_variant,
                    band_id,
                    "overlay_reference_no_overlap",
                    "overlay reference wavelengths do not overlap the canonical curve support",
                )
            )
            per_band[band_id] = {"error": "no overlap"}
            continue

        diff = sampled_response[overlap_mask] - reference_response[overlap_mask]
        band_max_abs_diff = float(np.max(np.abs(diff)))
        band_rmse = float(np.sqrt(np.mean(diff**2)))
        band_mean_abs_diff = float(np.mean(np.abs(diff)))
        max_abs_diff = max(max_abs_diff, band_max_abs_diff)
        rmse_max = max(rmse_max, band_rmse)
        if band_max_abs_diff > OVERLAY_MAX_ABS_TOLERANCE:
            failures.append(
                _failure(
                    sensor_unit_id,
                    representation_variant,
                    band_id,
                    "overlay_max_abs_diff",
                    (
                        f"overlay max absolute difference {band_max_abs_diff:.4f} exceeds "
                        f"tolerance {OVERLAY_MAX_ABS_TOLERANCE:.4f}"
                    ),
                )
            )

        per_band[band_id] = {
            "sample_count": int(reference_wavelength_nm.size),
            "max_abs_diff": band_max_abs_diff,
            "mean_abs_diff": band_mean_abs_diff,
            "rmse": band_rmse,
        }

    return {
        "required": required,
        "available": True,
        "reference_path": str(reference_path),
        "band_count": len(reference_curves),
        "max_abs_tolerance": OVERLAY_MAX_ABS_TOLERANCE,
        "max_abs_diff": max_abs_diff,
        "max_rmse": rmse_max,
        "per_band": per_band,
    }


def _overlay_reference_path(
    sensor_unit_id: str,
    representation_variant: str,
    *,
    root: Path | None,
) -> Path:
    layout = build_repo_layout(root)
    return (
        layout.extracted_sources_root
        / sensor_unit_id
        / representation_variant
        / OVERLAY_REFERENCE_FILENAME
    )


def _load_overlay_curve_pairs(
    sensor_unit_id: str,
    representation_variant: str,
    *,
    root: Path | None,
) -> list[tuple[SampledCurve, SampledCurve]]:
    reference_path = _overlay_reference_path(sensor_unit_id, representation_variant, root=root)
    if not reference_path.exists():
        return []
    reference_curves = _load_overlay_reference_curves(reference_path)
    curve_pairs: list[tuple[SampledCurve, SampledCurve]] = []
    for band_id in sorted(reference_curves):
        try:
            curve = load_curve(sensor_unit_id, band_id, representation_variant, root=root)
        except KeyError:
            continue
        curve_pairs.append((curve, reference_curves[band_id]))
    return curve_pairs


def _load_overlay_reference_curves(reference_path: Path) -> dict[str, SampledCurve]:
    rows_by_band: dict[str, list[tuple[float, float]]] = {}
    with reference_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            band_id = str(row["band_id"]).strip()
            rows_by_band.setdefault(band_id, []).append(
                (
                    float(row["wavelength_nm"]),
                    float(row["response"]),
                )
            )

    curves: dict[str, SampledCurve] = {}
    for band_id, rows in rows_by_band.items():
        rows.sort(key=lambda item: item[0])
        curves[band_id] = SampledCurve(
            band_id=band_id,
            wavelength_nm=np.asarray([item[0] for item in rows], dtype=float),
            response=np.asarray([item[1] for item in rows], dtype=float),
            source_variant="overlay_reference",
        )
    return curves


def _expected_band_count(metadata: dict[str, Any]) -> int | None:
    validation = metadata.get("manifest", {}).get("validation", {})
    value = validation.get("expected_band_count")
    return value if isinstance(value, int) else None


def _duplicate_values(values: list[int]) -> set[int]:
    seen: set[int] = set()
    duplicates: set[int] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return duplicates


def _failure(
    sensor_unit_id: str,
    representation_variant: str,
    band_id: str | None,
    check: str,
    message: str,
) -> dict[str, Any]:
    return {
        "sensor_unit_id": sensor_unit_id,
        "representation_variant": representation_variant,
        "band_id": band_id,
        "check": check,
        "message": message,
    }
