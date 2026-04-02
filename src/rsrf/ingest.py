"""Helpers for writing parsed ingest artifacts."""

from __future__ import annotations

import shutil
import tempfile
from datetime import datetime, timezone
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .io import parquet_support_available, write_json, write_parquet_table
from .models import BandSpec, ContentKind, SourceManifest
from .realize import estimate_center_wavelength, estimate_fwhm, realize_curve
from .registry import (
    canonical_variant_dir,
    realization_id_from_manifest,
    realized_variant_dir,
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

    # Write canonical artifacts to a staging directory first, then move
    # them into place so a partial failure does not leave corrupt state.
    staging_dir = Path(tempfile.mkdtemp(prefix="rsrf_ingest_"))
    try:
        staged_curves = staging_dir / "curves.parquet"
        staged_metadata = staging_dir / "metadata.json"
        write_parquet_table(
            staged_curves,
            artifacts.curve_rows,
            columns=CURVE_TABLE_COLUMNS,
        )
        write_json(staged_metadata, artifacts.metadata)

        # All writes succeeded — commit by moving files into place.
        output_dir.mkdir(parents=True, exist_ok=True)
        shutil.move(str(staged_curves), str(curves_path))
        shutil.move(str(staged_metadata), str(metadata_path))
    finally:
        shutil.rmtree(staging_dir, ignore_errors=True)

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
    realized_artifacts: ParsedArtifacts | None = None
    if manifest.curve_realization.persist_realized_curves:
        # Preflight derived-curve generation so unsupported recipes fail
        # before canonical files or registry rows are written.
        realized_artifacts = _build_realized_curve_artifacts(manifest, artifacts)

    output_dir = canonical_variant_dir(
        root,
        manifest.content_kind.value,
        manifest.sensor_unit_id,
        manifest.representation_variant,
    )
    band_specs_path = output_dir / "band_specs.parquet"
    metadata_path = output_dir / "metadata.json"

    staging_dir = Path(tempfile.mkdtemp(prefix="rsrf_ingest_"))
    try:
        staged_specs = staging_dir / "band_specs.parquet"
        staged_metadata = staging_dir / "metadata.json"
        write_parquet_table(
            staged_specs,
            artifacts.band_spec_rows,
            columns=BAND_SPEC_TABLE_COLUMNS,
        )
        write_json(staged_metadata, artifacts.metadata)

        output_dir.mkdir(parents=True, exist_ok=True)
        shutil.move(str(staged_specs), str(band_specs_path))
        shutil.move(str(staged_metadata), str(metadata_path))
    finally:
        shutil.rmtree(staging_dir, ignore_errors=True)

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
    if manifest.curve_realization.persist_realized_curves:
        realized = _write_realized_curve_artifacts(
            root,
            manifest,
            realized_artifacts,
        )
        written.update(realized)
    return written


def _write_realized_curve_artifacts(
    root: Path | None,
    manifest: SourceManifest,
    artifacts: ParsedArtifacts | None,
) -> dict[str, Path]:
    if not manifest.curve_realization.enabled:
        return {}
    if artifacts is None:
        raise ValueError("realized curve artifacts must be precomputed before writing")
    output_dir = realized_variant_dir(
        root,
        manifest.sensor_unit_id,
        manifest.curve_realization.output_representation_variant or "",
    )
    curves_path = output_dir / "curves.parquet"
    metadata_path = output_dir / "metadata.json"

    write_parquet_table(
        curves_path,
        artifacts.curve_rows,
        columns=CURVE_TABLE_COLUMNS,
    )
    write_json(metadata_path, artifacts.metadata)
    upsert_registry_rows(root, "bands", list(artifacts.band_rows))

    return {
        "realized_curves": curves_path,
        "realized_metadata": metadata_path,
        "bands_registry": registry_table_path(root, "bands"),
    }


def _build_realized_curve_artifacts(
    manifest: SourceManifest,
    artifacts: ParsedBandSpecArtifacts,
) -> ParsedArtifacts:
    realization = manifest.curve_realization
    if not realization.enabled:
        raise ValueError("curve_realization must be enabled to build realized curve artifacts")
    if realization.profile_type != "gaussian":
        raise NotImplementedError(
            f"unsupported realized profile_type: {realization.profile_type}"
        )
    if realization.grid_policy is None:
        raise ValueError("curve_realization.grid_policy is required for realized curves")

    grid_policy = realization.grid_policy
    output_variant = realization.output_representation_variant or ""
    realization_id = realization_id_from_manifest(manifest)
    curve_rows: list[dict[str, Any]] = []
    band_rows: list[dict[str, Any]] = []
    recovered_center_errors: list[float] = []
    recovered_fwhm_errors: list[float] = []

    for band_spec_row in artifacts.band_spec_rows:
        band_spec = BandSpec(
            band_id=str(band_spec_row["band_id"]),
            center_wavelength_nm=float(band_spec_row["center_wavelength_nm"]),
            fwhm_nm=float(band_spec_row["fwhm_nm"]),
            band_index=None
            if _is_nullish(band_spec_row["band_index"])
            else int(band_spec_row["band_index"]),
            band_name=str(band_spec_row["band_id"]),
            band_status=str(band_spec_row["band_status"]),
            published_shape_type=str(band_spec_row["published_shape_type"]),
            shape_param_json={},
        )
        curve = realize_curve(
            band_spec,
            profile_type=realization.profile_type or "gaussian",
            grid_policy=grid_policy,
            normalization=realization.normalization,
            source_variant=output_variant,
        )
        wavelength_nm = list(curve.wavelength_nm)
        response = list(curve.response)
        native_sampling_nm = None
        if len(wavelength_nm) > 1:
            native_sampling_nm = float(wavelength_nm[1] - wavelength_nm[0])
        support_min_nm = float(wavelength_nm[0])
        support_max_nm = float(wavelength_nm[-1])

        recovered_center_errors.append(
            abs(estimate_center_wavelength(curve) - band_spec.center_wavelength_nm)
        )
        recovered_fwhm_errors.append(abs(estimate_fwhm(curve) - band_spec.fwhm_nm))

        for wavelength, band_response in zip(wavelength_nm, response):
            curve_rows.append(
                {
                    "sensor_unit_id": manifest.sensor_unit_id,
                    "representation_variant": output_variant,
                    "band_id": band_spec.band_id,
                    "wavelength_nm": float(wavelength),
                    "response": float(band_response),
                    "curve_origin": "realized_parametric",
                    "realization_id": realization_id,
                    "is_native": False,
                    "is_trimmed": True,
                    "source_id": manifest.source_id,
                }
            )

        band_rows.append(
            {
                "sensor_unit_id": manifest.sensor_unit_id,
                "representation_variant": output_variant,
                "band_id": band_spec.band_id,
                "band_index": band_spec.band_index,
                "band_name": band_spec.band_name,
                "center_wavelength_nm": band_spec.center_wavelength_nm,
                "fwhm_nm": band_spec.fwhm_nm,
                "published_shape_type": realization.profile_type,
                "band_status": band_spec.band_status,
                "native_support_min_nm": support_min_nm,
                "native_support_max_nm": support_max_nm,
                "native_sampling_nm": native_sampling_nm,
                "normalization": realization.normalization,
                "has_sampled_curve": True,
                "has_band_spec": False,
            }
        )

    metadata = {
        "source_id": manifest.source_id,
        "sensor_unit_id": manifest.sensor_unit_id,
        "representation_variant": output_variant,
        "source_representation_variant": manifest.representation_variant,
        "content_kind": ContentKind.SAMPLED_CURVE.value,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "curve_table": {
            "row_count": len(curve_rows),
            "band_count": len(band_rows),
            "curve_origin": "realized_parametric",
        },
        "realization_id": realization_id,
        "realization": realization.to_dict(),
        "derived_from": {
            "content_kind": manifest.content_kind.value,
            "representation_variant": manifest.representation_variant,
        },
        "validation": {
            "max_center_abs_error_nm": max(recovered_center_errors) if recovered_center_errors else 0.0,
            "max_fwhm_abs_error_nm": max(recovered_fwhm_errors) if recovered_fwhm_errors else 0.0,
        },
        "manifest": manifest.to_dict(),
    }

    return ParsedArtifacts(
        curve_rows=curve_rows,
        band_rows=band_rows,
        metadata=metadata,
    )


def _is_nullish(value: Any) -> bool:
    return value is None or value != value
