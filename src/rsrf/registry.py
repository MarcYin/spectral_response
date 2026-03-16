"""Repository layout helpers and registry row builders."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from .io import read_parquet_table, upsert_parquet_table
from .models import ContentKind, SourceManifest, SourceType

REGISTRY_TABLES = ("sensors", "bands", "sources", "band_specs", "realizations")

REGISTRY_TABLE_COLUMNS = {
    "sensors": (
        "sensor_unit_id",
        "mission_family",
        "platform",
        "instrument",
        "representation_variant",
        "content_kind",
        "realization_kind",
        "spectral_calibration_scope",
        "spectral_domain",
        "source_tier",
        "approximation",
        "official_source_available",
        "band_count",
        "license_note",
        "status",
    ),
    "bands": (
        "sensor_unit_id",
        "representation_variant",
        "band_id",
        "band_index",
        "band_name",
        "center_wavelength_nm",
        "fwhm_nm",
        "published_shape_type",
        "band_status",
        "native_support_min_nm",
        "native_support_max_nm",
        "native_sampling_nm",
        "normalization",
        "has_sampled_curve",
        "has_band_spec",
    ),
    "sources": (
        "source_id",
        "sensor_unit_id",
        "representation_variant",
        "source_tier",
        "source_type",
        "content_kind",
        "title",
        "url",
        "retrieved_at",
        "file_sha256",
        "doc_version",
        "notes",
    ),
    "band_specs": (
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
    ),
    "realizations": (
        "realization_id",
        "sensor_unit_id",
        "source_representation_variant",
        "output_representation_variant",
        "profile_type",
        "profile_param_json",
        "grid_policy",
        "support_rule",
        "normalization",
        "approximation",
        "approximation_reason",
        "source_id",
    ),
}

REGISTRY_PRIMARY_KEYS = {
    "sensors": ("sensor_unit_id", "representation_variant"),
    "bands": ("sensor_unit_id", "representation_variant", "band_id"),
    "sources": ("source_id",),
    "band_specs": ("sensor_unit_id", "representation_variant", "band_id"),
    "realizations": ("realization_id",),
}


@dataclass(frozen=True)
class RepoLayout:
    """Resolved repository paths."""

    root: Path
    src_root: Path
    package_root: Path
    data_root: Path
    registry_root: Path
    canonical_root: Path
    realized_root: Path
    common_grid_root: Path
    docs_root: Path
    decisions_root: Path
    sensor_notes_root: Path
    scripts_root: Path
    ingest_scripts_root: Path
    build_scripts_root: Path
    validate_scripts_root: Path
    sources_root: Path
    raw_sources_root: Path
    extracted_sources_root: Path
    source_manifests_root: Path
    tests_root: Path


def discover_repo_root(start: Path | None = None) -> Path:
    """Walk upward until a repository root marker is found."""

    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "pyproject.toml").exists():
            return candidate
        if (candidate / ".git").exists():
            return candidate
    return current


def build_repo_layout(root: Path | None = None) -> RepoLayout:
    """Build the standard repository layout."""

    repo_root = discover_repo_root(root)
    return RepoLayout(
        root=repo_root,
        src_root=repo_root / "src",
        package_root=repo_root / "src" / "rsrf",
        data_root=repo_root / "data",
        registry_root=repo_root / "data" / "registry",
        canonical_root=repo_root / "data" / "canonical",
        realized_root=repo_root / "data" / "realized",
        common_grid_root=repo_root / "data" / "common_grid",
        docs_root=repo_root / "docs",
        decisions_root=repo_root / "docs" / "decisions",
        sensor_notes_root=repo_root / "docs" / "sensor-notes",
        scripts_root=repo_root / "scripts",
        ingest_scripts_root=repo_root / "scripts" / "ingest",
        build_scripts_root=repo_root / "scripts" / "build",
        validate_scripts_root=repo_root / "scripts" / "validate",
        sources_root=repo_root / "sources",
        raw_sources_root=repo_root / "sources" / "raw",
        extracted_sources_root=repo_root / "sources" / "extracted",
        source_manifests_root=repo_root / "sources" / "manifests",
        tests_root=repo_root / "tests",
    )


def ensure_repo_layout(root: Path | None = None) -> RepoLayout:
    """Create the standard directories if they do not exist."""

    layout = build_repo_layout(root)
    paths: Iterable[Path] = (
        layout.src_root,
        layout.package_root,
        layout.data_root,
        layout.registry_root,
        layout.canonical_root,
        layout.realized_root,
        layout.common_grid_root,
        layout.docs_root,
        layout.decisions_root,
        layout.sensor_notes_root,
        layout.scripts_root,
        layout.ingest_scripts_root,
        layout.build_scripts_root,
        layout.validate_scripts_root,
        layout.sources_root,
        layout.raw_sources_root,
        layout.extracted_sources_root,
        layout.source_manifests_root,
        layout.tests_root,
    )
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)
    return layout


def registry_table_path(root: Path | None, table_name: str) -> Path:
    """Return the parquet path for a named registry table."""

    if table_name not in REGISTRY_TABLES:
        raise ValueError(f"unknown registry table: {table_name}")
    layout = build_repo_layout(root)
    return layout.registry_root / f"{table_name}.parquet"


def registry_table_columns(table_name: str) -> tuple[str, ...]:
    """Return the canonical column order for a registry table."""

    if table_name not in REGISTRY_TABLE_COLUMNS:
        raise ValueError(f"unknown registry table: {table_name}")
    return tuple(REGISTRY_TABLE_COLUMNS[table_name])


def registry_primary_key(table_name: str) -> tuple[str, ...]:
    """Return the primary-key column set for a registry table."""

    if table_name not in REGISTRY_PRIMARY_KEYS:
        raise ValueError(f"unknown registry table: {table_name}")
    return tuple(REGISTRY_PRIMARY_KEYS[table_name])


def canonical_variant_dir(
    root: Path | None,
    content_kind: str,
    sensor_unit_id: str,
    representation_variant: str,
) -> Path:
    """Return the canonical output directory for a sensor variant."""

    layout = build_repo_layout(root)
    return (
        layout.canonical_root
        / content_kind
        / sensor_unit_id
        / representation_variant
    )


def sensor_row_from_manifest(
    manifest: SourceManifest,
    *,
    representation_variant: str | None = None,
    content_kind: ContentKind | None = None,
    realization_kind: str = "none",
    approximation: bool = False,
    status: str = "registered",
) -> dict[str, Any]:
    """Build the canonical sensor registry row for a manifest."""

    band_count = (
        manifest.validation.expected_band_count
        if isinstance(manifest.validation.expected_band_count, int)
        else None
    )
    return {
        "sensor_unit_id": manifest.sensor_unit_id,
        "mission_family": None,
        "platform": None,
        "instrument": None,
        "representation_variant": representation_variant or manifest.representation_variant,
        "content_kind": (content_kind or manifest.content_kind).value,
        "realization_kind": realization_kind,
        "spectral_calibration_scope": manifest.canonical.spectral_calibration_scope,
        "spectral_domain": manifest.validation.expected_domain,
        "source_tier": manifest.source_tier.value,
        "approximation": approximation,
        "official_source_available": manifest.source_type
        in {SourceType.OFFICIAL, SourceType.OFFICIAL_METADATA},
        "band_count": band_count,
        "license_note": manifest.license_note,
        "status": status,
    }


def source_row_from_manifest(manifest: SourceManifest) -> dict[str, Any]:
    """Build the source registry row for a manifest."""

    return {
        "source_id": manifest.source_id,
        "sensor_unit_id": manifest.sensor_unit_id,
        "representation_variant": manifest.representation_variant,
        "source_tier": manifest.source_tier.value,
        "source_type": manifest.source_type.value,
        "content_kind": manifest.content_kind.value,
        "title": manifest.title,
        "url": manifest.url,
        "retrieved_at": manifest.retrieved_at,
        "file_sha256": manifest.file_sha256,
        "doc_version": manifest.doc_version,
        "notes": json.dumps(list(manifest.notes), sort_keys=True),
    }


def realization_row_from_manifest(manifest: SourceManifest) -> dict[str, Any] | None:
    """Build a realization registry row when the manifest declares one."""

    if not manifest.curve_realization.enabled:
        return None

    grid_policy = (
        manifest.curve_realization.grid_policy.to_dict()
        if manifest.curve_realization.grid_policy is not None
        else {}
    )
    truncate_sigma = grid_policy.get("truncate_sigma")
    support_rule = (
        f"center_plus_minus_{truncate_sigma}_sigma"
        if truncate_sigma is not None
        else "manifest_defined"
    )
    realization_id = (
        f"{manifest.sensor_unit_id}."
        f"{manifest.representation_variant}."
        f"{manifest.curve_realization.output_representation_variant}"
    )

    return {
        "realization_id": realization_id,
        "sensor_unit_id": manifest.sensor_unit_id,
        "source_representation_variant": manifest.representation_variant,
        "output_representation_variant": manifest.curve_realization.output_representation_variant,
        "profile_type": manifest.curve_realization.profile_type,
        "profile_param_json": json.dumps({}, sort_keys=True),
        "grid_policy": json.dumps(grid_policy, sort_keys=True),
        "support_rule": support_rule,
        "normalization": manifest.curve_realization.normalization,
        "approximation": manifest.curve_realization.approximation,
        "approximation_reason": manifest.curve_realization.approximation_reason,
        "source_id": manifest.source_id,
    }


def manifest_registry_rows(
    manifest: SourceManifest,
    *,
    status: str = "registered",
) -> dict[str, list[Mapping[str, Any]]]:
    """Convert a manifest into normalized registry rows."""

    rows: dict[str, list[Mapping[str, Any]]] = {table_name: [] for table_name in REGISTRY_TABLES}
    rows["sensors"].append(sensor_row_from_manifest(manifest, status=status))
    rows["sources"].append(source_row_from_manifest(manifest))

    realization_row = realization_row_from_manifest(manifest)
    if realization_row is not None:
        rows["sensors"].append(
            sensor_row_from_manifest(
                manifest,
                representation_variant=manifest.curve_realization.output_representation_variant,
                content_kind=ContentKind.SAMPLED_CURVE,
                realization_kind=(
                    "approximate_parametric"
                    if manifest.curve_realization.approximation
                    else "official_parametric"
                ),
                approximation=manifest.curve_realization.approximation,
                status=status,
            )
        )
        rows["realizations"].append(realization_row)

    return rows


def read_registry_table(root: Path | None, table_name: str):
    """Read a registry table from its parquet path."""

    return read_parquet_table(registry_table_path(root, table_name))


def upsert_registry_rows(
    root: Path | None,
    table_name: str,
    rows: list[Mapping[str, Any]],
):
    """Upsert rows into a named registry table."""

    if table_name not in REGISTRY_TABLES:
        raise ValueError(f"unknown registry table: {table_name}")
    if not rows:
        return None
    return upsert_parquet_table(
        registry_table_path(root, table_name),
        rows,
        key_columns=registry_primary_key(table_name),
        columns=registry_table_columns(table_name),
    )


def register_manifest(
    root: Path | None,
    manifest: SourceManifest,
    *,
    status: str = "registered",
) -> dict[str, Path]:
    """Write manifest-derived rows into the registry tables."""

    written: dict[str, Path] = {}
    rows_by_table = manifest_registry_rows(manifest, status=status)
    for table_name, rows in rows_by_table.items():
        path = upsert_registry_rows(root, table_name, rows)
        if path is not None:
            written[table_name] = path
    return written
