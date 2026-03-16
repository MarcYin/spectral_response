"""Read API for registry-backed spectral response data."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .io import read_json
from .models import BandSpec, ContentKind, SampledCurve
from .registry import canonical_variant_dir, read_registry_table


def list_sensors(root: Path | None = None) -> list[dict[str, Any]]:
    """List registered sensor representations."""

    frame = _available_sensor_rows(root)
    frame = frame.sort_values(["sensor_unit_id", "representation_variant"])
    return frame.to_dict(orient="records")


def list_bands(
    sensor_unit_id: str,
    representation_variant: str | None = None,
    *,
    root: Path | None = None,
) -> list[dict[str, Any]]:
    """List bands for a sensor representation."""

    resolved_variant, _ = _resolve_sensor_variant(
        sensor_unit_id,
        representation_variant,
        root=root,
    )
    frame = read_registry_table(root, "bands")
    frame = frame[
        (frame["sensor_unit_id"] == sensor_unit_id)
        & (frame["representation_variant"] == resolved_variant)
    ]
    if "band_index" in frame.columns:
        frame = frame.sort_values(["band_index", "band_id"], na_position="last")
    return frame.to_dict(orient="records")


def get_metadata(
    sensor_unit_id: str,
    representation_variant: str | None = None,
    *,
    root: Path | None = None,
) -> dict[str, Any]:
    """Load the canonical metadata sidecar for a sensor representation."""

    resolved_variant, content_kind = _resolve_sensor_variant(
        sensor_unit_id,
        representation_variant,
        root=root,
    )
    metadata_path = (
        canonical_variant_dir(root, content_kind.value, sensor_unit_id, resolved_variant)
        / "metadata.json"
    )
    return read_json(metadata_path)


def load_curve(
    sensor_unit_id: str,
    band_id: str,
    representation_variant: str | None = None,
    *,
    root: Path | None = None,
) -> SampledCurve:
    """Load a canonical sampled curve for a band."""

    resolved_variant, content_kind = _resolve_sensor_variant(
        sensor_unit_id,
        representation_variant,
        root=root,
    )
    if content_kind != ContentKind.SAMPLED_CURVE:
        raise ValueError(
            f"{sensor_unit_id}/{resolved_variant} is {content_kind.value}, not sampled_curve"
        )

    curves_path = (
        canonical_variant_dir(root, content_kind.value, sensor_unit_id, resolved_variant)
        / "curves.parquet"
    )
    frame = _read_parquet(curves_path)
    frame = frame[
        (frame["sensor_unit_id"] == sensor_unit_id)
        & (frame["representation_variant"] == resolved_variant)
        & (frame["band_id"] == band_id)
    ]
    if frame.empty:
        raise KeyError(f"curve not found for {sensor_unit_id}/{resolved_variant}/{band_id}")
    frame = frame.sort_values("wavelength_nm")
    return SampledCurve(
        band_id=band_id,
        wavelength_nm=frame["wavelength_nm"].to_numpy(),
        response=frame["response"].to_numpy(),
        source_variant=resolved_variant,
    )


def load_band_spec(
    sensor_unit_id: str,
    band_id: str,
    representation_variant: str | None = None,
    *,
    root: Path | None = None,
) -> BandSpec:
    """Load a canonical band specification for a band."""

    resolved_variant, content_kind = _resolve_sensor_variant(
        sensor_unit_id,
        representation_variant,
        root=root,
    )
    if content_kind != ContentKind.BAND_SPEC:
        raise ValueError(f"{sensor_unit_id}/{resolved_variant} is not a band_spec representation")

    band_specs_path = (
        canonical_variant_dir(root, content_kind.value, sensor_unit_id, resolved_variant)
        / "band_specs.parquet"
    )
    frame = _read_parquet(band_specs_path)
    frame = frame[
        (frame["sensor_unit_id"] == sensor_unit_id)
        & (frame["representation_variant"] == resolved_variant)
        & (frame["band_id"] == band_id)
    ]
    if frame.empty:
        raise KeyError(f"band spec not found for {sensor_unit_id}/{resolved_variant}/{band_id}")
    row = frame.iloc[0]
    shape_param_json = row["shape_param_json"]
    return BandSpec(
        band_id=str(row["band_id"]),
        center_wavelength_nm=float(row["center_wavelength_nm"]),
        fwhm_nm=float(row["fwhm_nm"]),
        band_index=None if _is_nullish(row["band_index"]) else int(row["band_index"]),
        band_name=str(row["band_id"]),
        band_status="nominal" if _is_nullish(row["band_status"]) else str(row["band_status"]),
        published_shape_type=str(row["published_shape_type"]),
        shape_param_json=(
            {}
            if _is_nullish(shape_param_json) or not shape_param_json
            else json.loads(shape_param_json)
        ),
    )


def load_response_definition(
    sensor_unit_id: str,
    band_id: str,
    representation_variant: str | None = None,
    *,
    root: Path | None = None,
) -> SampledCurve | BandSpec:
    """Load either a sampled curve or a canonical band spec for a band."""

    resolved_variant, content_kind = _resolve_sensor_variant(
        sensor_unit_id,
        representation_variant,
        root=root,
    )
    if content_kind == ContentKind.SAMPLED_CURVE:
        return load_curve(sensor_unit_id, band_id, resolved_variant, root=root)
    if content_kind == ContentKind.BAND_SPEC:
        return load_band_spec(sensor_unit_id, band_id, resolved_variant, root=root)
    raise NotImplementedError(f"content_kind not supported: {content_kind.value}")


def _resolve_sensor_variant(
    sensor_unit_id: str,
    representation_variant: str | None,
    *,
    root: Path | None = None,
) -> tuple[str, ContentKind]:
    sensors = _available_sensor_rows(root)
    frame = sensors[sensors["sensor_unit_id"] == sensor_unit_id]
    if representation_variant is not None:
        frame = frame[frame["representation_variant"] == representation_variant]
    if frame.empty:
        raise KeyError(f"sensor representation not found: {sensor_unit_id}/{representation_variant}")
    if len(frame) > 1:
        raise ValueError(
            f"multiple representations found for {sensor_unit_id}; representation_variant is required"
        )
    row = frame.iloc[0]
    return str(row["representation_variant"]), ContentKind(str(row["content_kind"]))


def _available_sensor_rows(root: Path | None):
    frame = read_registry_table(root, "sensors")
    mask = frame.apply(_row_has_backing_artifact, axis=1, root=root)
    return frame[mask].copy()


def _row_has_backing_artifact(row, *, root: Path | None) -> bool:
    content_kind = ContentKind(str(row["content_kind"]))
    artifact_name = _primary_artifact_name(content_kind)
    if artifact_name is None:
        return False
    artifact_path = (
        canonical_variant_dir(
            root,
            content_kind.value,
            str(row["sensor_unit_id"]),
            str(row["representation_variant"]),
        )
        / artifact_name
    )
    return artifact_path.exists()


def _primary_artifact_name(content_kind: ContentKind) -> str | None:
    if content_kind == ContentKind.SAMPLED_CURVE:
        return "curves.parquet"
    if content_kind == ContentKind.BAND_SPEC:
        return "band_specs.parquet"
    return None


def _is_nullish(value: Any) -> bool:
    return value is None or value != value


def _read_parquet(path: Path):
    try:
        import pandas as pd
    except ImportError as exc:
        raise RuntimeError("pandas is required for read API operations") from exc

    return pd.read_parquet(path)
