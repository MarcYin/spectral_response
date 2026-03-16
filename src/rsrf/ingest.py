"""Helpers for writing parsed ingest artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .io import parquet_support_available, write_json, write_parquet_table
from .models import ContentKind, SourceManifest
from .registry import (
    canonical_variant_dir,
    register_manifest,
    registry_table_columns,
    registry_table_path,
    upsert_registry_rows,
)

CURVE_TABLE_COLUMNS = (
    "sensor_unit_id",
    "representation_variant",
    "band_id",
    "wavelength_nm",
    "response",
    "curve_origin",
    "realization_id",
    "is_native",
    "is_trimmed",
    "source_id",
)

BAND_SPEC_TABLE_COLUMNS = (
    "sensor_unit_id",
    "representation_variant",
    "band_id",
    "band_index",
    "center_wavelength_nm",
    "fwhm_nm",
    "published_shape_type",
    "shape_param_json",
    "band_status",
    "is_official",
    "source_id",
)


@dataclass(frozen=True)
class ParsedArtifacts:
    """Parsed canonical outputs ready to be written."""

    curve_rows: list[Mapping[str, Any]]
    band_rows: list[Mapping[str, Any]]
    metadata: Mapping[str, Any]


@dataclass(frozen=True)
class ParsedBandSpecArtifacts:
    """Parsed band-spec outputs ready to be written."""

    band_spec_rows: list[Mapping[str, Any]]
    band_rows: list[Mapping[str, Any]]
    metadata: Mapping[str, Any]


def write_sampled_curve_artifacts(
    root: Path | None,
    manifest: SourceManifest,
    artifacts: ParsedArtifacts,
) -> dict[str, Path]:
    """Write sampled-curve artifacts and update registry tables."""

    if manifest.content_kind != ContentKind.SAMPLED_CURVE:
        raise ValueError("write_sampled_curve_artifacts requires a sampled_curve manifest")
    if not parquet_support_available():
        raise RuntimeError(
            "Parquet support requires either pyarrow or fastparquet in the Python environment"
        )

    output_dir = canonical_variant_dir(
        root,
        manifest.content_kind.value,
        manifest.sensor_unit_id,
        manifest.representation_variant,
    )
    curves_path = output_dir / "curves.parquet"
    metadata_path = output_dir / "metadata.json"

    write_parquet_table(
        curves_path,
        artifacts.curve_rows,
        columns=CURVE_TABLE_COLUMNS,
    )
    write_json(metadata_path, artifacts.metadata)
    register_manifest(root, manifest)
    upsert_registry_rows(root, "bands", list(artifacts.band_rows))

    return {
        "curves": curves_path,
        "metadata": metadata_path,
        "bands_registry": registry_table_path(root, "bands"),
        "sensors_registry": registry_table_path(root, "sensors"),
        "sources_registry": registry_table_path(root, "sources"),
    }


def write_band_spec_artifacts(
    root: Path | None,
    manifest: SourceManifest,
    artifacts: ParsedBandSpecArtifacts,
) -> dict[str, Path]:
    """Write band-spec artifacts and update registry tables."""

    if manifest.content_kind != ContentKind.BAND_SPEC:
        raise ValueError("write_band_spec_artifacts requires a band_spec manifest")
    if not parquet_support_available():
        raise RuntimeError(
            "Parquet support requires either pyarrow or fastparquet in the Python environment"
        )

    output_dir = canonical_variant_dir(
        root,
        manifest.content_kind.value,
        manifest.sensor_unit_id,
        manifest.representation_variant,
    )
    band_specs_path = output_dir / "band_specs.parquet"
    metadata_path = output_dir / "metadata.json"

    write_parquet_table(
        band_specs_path,
        artifacts.band_spec_rows,
        columns=BAND_SPEC_TABLE_COLUMNS,
    )
    write_json(metadata_path, artifacts.metadata)
    register_manifest(root, manifest)
    upsert_registry_rows(root, "band_specs", list(artifacts.band_spec_rows))
    upsert_registry_rows(root, "bands", list(artifacts.band_rows))

    written = {
        "band_specs": band_specs_path,
        "metadata": metadata_path,
        "band_specs_registry": registry_table_path(root, "band_specs"),
        "bands_registry": registry_table_path(root, "bands"),
        "sensors_registry": registry_table_path(root, "sensors"),
        "sources_registry": registry_table_path(root, "sources"),
    }
    if manifest.curve_realization.enabled:
        written["realizations_registry"] = registry_table_path(root, "realizations")
    return written
