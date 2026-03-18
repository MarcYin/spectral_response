"""Helpers for building interactive documentation visualization assets."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from .api import list_bands, list_sensors, load_response_definition
from .convolve import response_area
from .models import BandSpec, SampledCurve
from .realize import realize_curve
from .registry import build_repo_layout

DOCS_WAVELENGTH_MIN_NM = 300
DOCS_WAVELENGTH_MAX_NM = 2500
DOCS_WAVELENGTH_STEP_NM = 1
DISPLAY_MAX_POINTS = 800
SUPPORT_THRESHOLD = 0.001
NUMERIC_PAN_SENSOR_KEYS = {
    "landsat-7_etm_plus",
    "landsat-8_oli",
    "landsat-9_oli2",
}
PAN_BAND_RE = re.compile(r"\bpan(chromatic)?\b", re.IGNORECASE)


def export_docs_visualization_assets(
    root: Path | None = None,
    *,
    output_dir: Path | None = None,
    sensor_keys: Iterable[tuple[str, str]] | None = None,
) -> dict[str, Path]:
    """Export interactive documentation assets for sensor visualization."""

    layout = build_repo_layout(root)
    resolved_root = layout.root
    output_root = (
        output_dir
        if output_dir is not None
        else layout.docs_root / "assets" / "visualization"
    ).resolve()
    sensors_root = output_root / "sensors"
    output_root.mkdir(parents=True, exist_ok=True)
    sensors_root.mkdir(parents=True, exist_ok=True)

    allowed_keys = None if sensor_keys is None else set(sensor_keys)
    sensor_rows = [
        row
        for row in list_sensors(root=resolved_root)
        if allowed_keys is None
        or (str(row["sensor_unit_id"]), str(row["representation_variant"])) in allowed_keys
    ]
    sensor_rows.sort(key=lambda row: (str(row["sensor_unit_id"]), str(row["representation_variant"])))

    wavelength_grid_nm = np.arange(
        DOCS_WAVELENGTH_MIN_NM,
        DOCS_WAVELENGTH_MAX_NM + DOCS_WAVELENGTH_STEP_NM,
        DOCS_WAVELENGTH_STEP_NM,
        dtype=float,
    )

    sensor_index_rows: list[dict[str, Any]] = []
    overlap_index_rows: list[dict[str, Any]] = []
    heatmap_rows_all: list[list[float]] = []
    heatmap_rows_no_pan: list[list[float]] = []

    for sensor_row in sensor_rows:
        sensor_payload, heatmap_rows = _build_sensor_visualization_payload(
            resolved_root,
            sensor_row,
            wavelength_grid_nm,
        )
        sensor_filename = _sensor_filename(
            str(sensor_row["sensor_unit_id"]),
            str(sensor_row["representation_variant"]),
        )
        sensor_file_path = sensors_root / sensor_filename
        _write_json(sensor_file_path, sensor_payload)

        index_row = {
            "sensor_key": sensor_payload["sensor_key"],
            "label": sensor_payload["label"],
            "sensor_unit_id": sensor_payload["sensor_unit_id"],
            "representation_variant": sensor_payload["representation_variant"],
            "mission_family": sensor_payload["mission_family"],
            "platform": sensor_payload["platform"],
            "instrument": sensor_payload["instrument"],
            "content_kind": sensor_payload["content_kind"],
            "spectral_domain": sensor_payload["spectral_domain"],
            "band_count": sensor_payload["band_count"],
            "pan_band_count": sensor_payload["pan_band_count"],
            "curve_origin": sensor_payload["curve_origin"],
            "wavelength_min_nm": sensor_payload["wavelength_min_nm"],
            "wavelength_max_nm": sensor_payload["wavelength_max_nm"],
            "sensor_file": f"sensors/{sensor_filename}",
        }
        sensor_index_rows.append(index_row)
        overlap_index_rows.append(
            {
                **index_row,
                "bands": sensor_payload["bands"],
            }
        )
        heatmap_rows_all.append(_round_array(heatmap_rows["all_bands"], digits=4))
        heatmap_rows_no_pan.append(_round_array(heatmap_rows["no_pan"], digits=4))

    index_payload = {
        "grid": {
            "min_nm": DOCS_WAVELENGTH_MIN_NM,
            "max_nm": DOCS_WAVELENGTH_MAX_NM,
            "step_nm": DOCS_WAVELENGTH_STEP_NM,
            "wavelength_nm": _round_array(wavelength_grid_nm, digits=1),
        },
        "heatmap": {
            "default_mode": "no_pan",
            "z": heatmap_rows_no_pan,
            "modes": {
                "all_bands": {
                    "description": (
                        "Peak-normalized per-sensor maximum response across all bands on a 1 nm grid."
                    ),
                    "z": heatmap_rows_all,
                },
                "no_pan": {
                    "description": (
                        "Peak-normalized per-sensor maximum response with Pan/panchromatic bands excluded."
                    ),
                    "z": heatmap_rows_no_pan,
                },
            },
        },
        "sensors": sensor_index_rows,
    }
    overlap_index_payload = {
        "sensors": overlap_index_rows,
    }

    index_path = output_root / "index.json"
    overlap_index_path = output_root / "overlap_index.json"
    _write_json(index_path, index_payload)
    _write_json(overlap_index_path, overlap_index_payload)
    return {
        "index": index_path,
        "overlap_index": overlap_index_path,
        "sensor_dir": sensors_root,
    }


def _build_sensor_visualization_payload(
    root: Path,
    sensor_row: dict[str, Any],
    wavelength_grid_nm: np.ndarray,
) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    sensor_unit_id = str(sensor_row["sensor_unit_id"])
    representation_variant = str(sensor_row["representation_variant"])
    bands = list_bands(sensor_unit_id, representation_variant, root=root)

    band_payloads: list[dict[str, Any]] = []
    heatmap_rows = {
        "all_bands": np.zeros_like(wavelength_grid_nm, dtype=float),
        "no_pan": np.zeros_like(wavelength_grid_nm, dtype=float),
    }
    sensor_support_min = float("inf")
    sensor_support_max = float("-inf")
    curve_origins: set[str] = set()
    pan_band_count = 0

    for band_row in bands:
        band_id = str(band_row["band_id"])
        band_name = _clean_optional_text(band_row.get("band_name")) or band_id
        is_pan_band = _is_pan_band(sensor_unit_id, band_id, band_name)
        response_definition = load_response_definition(
            sensor_unit_id,
            band_id,
            representation_variant,
            root=root,
        )
        curve, curve_origin = _as_curve(response_definition)
        normalized_curve = _normalize_curve(curve)
        support_min_nm, support_max_nm = _curve_support_bounds(normalized_curve)

        sensor_support_min = min(sensor_support_min, support_min_nm)
        sensor_support_max = max(sensor_support_max, support_max_nm)
        curve_origins.add(curve_origin)
        if is_pan_band:
            pan_band_count += 1

        interpolated_curve = np.interp(
            wavelength_grid_nm,
            np.asarray(normalized_curve.wavelength_nm, dtype=float),
            np.asarray(normalized_curve.response, dtype=float),
            left=0.0,
            right=0.0,
        )
        heatmap_rows["all_bands"] = np.maximum(
            heatmap_rows["all_bands"],
            interpolated_curve,
        )
        if not is_pan_band:
            heatmap_rows["no_pan"] = np.maximum(
                heatmap_rows["no_pan"],
                interpolated_curve,
            )

        display_curve = _downsample_curve(curve, max_points=DISPLAY_MAX_POINTS)
        band_payloads.append(
            {
                "band_id": band_id,
                "band_name": band_name,
                "band_index": _clean_optional_int(band_row.get("band_index")),
                "curve_origin": curve_origin,
                "is_pan_band": is_pan_band,
                "center_wavelength_nm": _clean_optional_float(
                    band_row.get("center_wavelength_nm")
                ),
                "fwhm_nm": _clean_optional_float(band_row.get("fwhm_nm")),
                "support_min_nm": round(support_min_nm, 3),
                "support_max_nm": round(support_max_nm, 3),
                "native_point_count": int(len(curve.wavelength_nm)),
                "display_point_count": int(len(display_curve.wavelength_nm)),
                "peak_response": round(float(np.max(np.asarray(curve.response, dtype=float))), 6),
                "area": round(float(response_area(curve)), 6),
                "points": [
                    [round(float(wavelength_nm), 4), round(float(response), 6)]
                    for wavelength_nm, response in zip(
                        np.asarray(display_curve.wavelength_nm, dtype=float),
                        np.asarray(display_curve.response, dtype=float),
                    )
                ],
            }
        )

    curve_origin = (
        next(iter(curve_origins))
        if len(curve_origins) == 1
        else "mixed"
    )
    sensor_payload = {
        "sensor_key": _sensor_key(sensor_unit_id, representation_variant),
        "label": _sensor_label(sensor_row),
        "sensor_unit_id": sensor_unit_id,
        "representation_variant": representation_variant,
        "mission_family": _clean_optional_text(sensor_row.get("mission_family")),
        "platform": _clean_optional_text(sensor_row.get("platform")),
        "instrument": _clean_optional_text(sensor_row.get("instrument")),
        "content_kind": str(sensor_row["content_kind"]),
        "spectral_domain": _clean_optional_text(sensor_row.get("spectral_domain")),
        "curve_origin": curve_origin,
        "band_count": len(band_payloads),
        "pan_band_count": pan_band_count,
        "wavelength_min_nm": round(sensor_support_min, 3),
        "wavelength_max_nm": round(sensor_support_max, 3),
        "bands": band_payloads,
    }
    return sensor_payload, heatmap_rows


def _as_curve(response_definition: SampledCurve | BandSpec) -> tuple[SampledCurve, str]:
    if isinstance(response_definition, SampledCurve):
        return response_definition, "sampled_curve"
    if isinstance(response_definition, BandSpec):
        return realize_curve(response_definition), "realized_band_spec"
    raise TypeError(f"unsupported response definition type: {type(response_definition)!r}")


def _normalize_curve(curve: SampledCurve) -> SampledCurve:
    response = np.asarray(curve.response, dtype=float)
    peak = float(response.max())
    if peak <= 0.0:
        raise ValueError(f"curve {curve.band_id} has nonpositive peak response")
    return SampledCurve(
        band_id=curve.band_id,
        wavelength_nm=np.asarray(curve.wavelength_nm, dtype=float),
        response=response / peak,
        source_variant=curve.source_variant,
    )


def _curve_support_bounds(curve: SampledCurve) -> tuple[float, float]:
    wavelength_nm = np.asarray(curve.wavelength_nm, dtype=float)
    response = np.asarray(curve.response, dtype=float)
    peak = float(response.max())
    if peak <= 0.0:
        return float(wavelength_nm[0]), float(wavelength_nm[-1])
    mask = response >= peak * SUPPORT_THRESHOLD
    if not np.any(mask):
        return float(wavelength_nm[0]), float(wavelength_nm[-1])
    return float(wavelength_nm[mask][0]), float(wavelength_nm[mask][-1])


def _downsample_curve(curve: SampledCurve, *, max_points: int) -> SampledCurve:
    wavelength_nm = np.asarray(curve.wavelength_nm, dtype=float)
    response = np.asarray(curve.response, dtype=float)
    if len(wavelength_nm) <= max_points:
        return curve
    indices = np.linspace(0, len(wavelength_nm) - 1, num=max_points, dtype=int)
    indices = np.unique(indices)
    return SampledCurve(
        band_id=curve.band_id,
        wavelength_nm=wavelength_nm[indices],
        response=response[indices],
        source_variant=curve.source_variant,
    )


def _sensor_key(sensor_unit_id: str, representation_variant: str) -> str:
    return f"{sensor_unit_id}__{representation_variant}"


def _sensor_filename(sensor_unit_id: str, representation_variant: str) -> str:
    return f"{_sensor_key(sensor_unit_id, representation_variant)}.json"


def _sensor_label(sensor_row: dict[str, Any]) -> str:
    platform = _clean_optional_text(sensor_row.get("platform"))
    instrument = _clean_optional_text(sensor_row.get("instrument"))
    sensor_unit_id = str(sensor_row["sensor_unit_id"])
    representation_variant = str(sensor_row["representation_variant"])
    core_label = sensor_unit_id
    if platform and instrument:
        core_label = f"{platform} {instrument}"
    elif platform:
        core_label = platform
    elif instrument:
        core_label = f"{sensor_unit_id} {instrument}"
    return f"{core_label} / {representation_variant}"


def _is_pan_band(sensor_unit_id: str, band_id: str, band_name: str | None) -> bool:
    band_text = f"{band_id} {band_name or ''}".strip().lower()
    if PAN_BAND_RE.search(band_text):
        return True
    return sensor_unit_id in NUMERIC_PAN_SENSOR_KEYS and band_id.upper() == "B8"


def _clean_optional_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, float) and np.isnan(value):
        return None
    text = str(value).strip()
    return text or None


def _clean_optional_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, float) and np.isnan(value):
        return None
    if hasattr(value, "item") and callable(value.item):
        value = value.item()
    return round(float(value), 6)


def _clean_optional_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, float) and np.isnan(value):
        return None
    if hasattr(value, "item") and callable(value.item):
        value = value.item()
    return int(value)


def _round_array(values: np.ndarray, *, digits: int) -> list[float]:
    rounded = np.round(np.asarray(values, dtype=float), decimals=digits)
    return [float(value) for value in rounded.tolist()]


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(",", ":")),
        encoding="utf-8",
    )
