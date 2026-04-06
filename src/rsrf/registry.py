"""Repository layout helpers and registry row builders."""

from __future__ import annotations

import json
import os
import shutil
import sys
import tarfile
import tempfile
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as distribution_version
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .io import ensure_directory, read_parquet_table, upsert_parquet_table, write_json
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

RSRF_ROOT_ENV_VAR = "RSRF_ROOT"
RSRF_CACHE_DIR_ENV_VAR = "RSRF_CACHE_DIR"
RUNTIME_RELEASE_REPOSITORY = "MarcYin/spectral_response"
RUNTIME_RELEASE_ASSET_NAME_TEMPLATE = "rsrf-root-v{version}.tar.gz"
RUNTIME_RELEASE_ASSET_URL_TEMPLATE = (
    "https://github.com/{repository}/releases/download/v{version}/{asset_name}"
)
RUNTIME_SOURCE_ARCHIVE_URL_TEMPLATE = "https://github.com/{repository}/archive/refs/tags/v{version}.tar.gz"
RUNTIME_MAIN_ARCHIVE_URL_TEMPLATE = "https://github.com/{repository}/archive/refs/heads/main.tar.gz"
RUNTIME_READY_MARKER_FILENAME = ".rsrf-runtime-root.json"


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
    official_source_manifests_root: Path
    planning_source_manifests_root: Path
    template_source_manifests_root: Path
    tests_root: Path


def discover_repo_root(start: Path | None = None) -> Path:
    """Resolve the active RSRF root.

    Explicit roots and ``RSRF_ROOT`` override discovery. When neither is
    provided, RSRF prefers a local repository checkout and otherwise
    bootstraps a cached GitHub release snapshot for the installed version.
    """

    explicit_root = _resolve_supplied_root(start)
    if explicit_root is not None:
        return explicit_root

    environment_root = _resolve_environment_root()
    if environment_root is not None:
        return environment_root

    cwd_root = _discover_repo_root_from_directory(Path.cwd().resolve())
    if cwd_root is not None:
        return cwd_root

    package_root = _package_checkout_root()
    if package_root is not None:
        return package_root

    return _runtime_release_root()


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
        official_source_manifests_root=repo_root / "sources" / "manifests" / "official",
        planning_source_manifests_root=repo_root / "sources" / "manifests" / "planning",
        template_source_manifests_root=repo_root / "sources" / "manifests" / "templates",
        tests_root=repo_root / "tests",
    )


def _resolve_supplied_root(root: Path | None) -> Path | None:
    if root is None:
        return None
    candidate = Path(root).expanduser().resolve()
    if not candidate.exists():
        raise FileNotFoundError(f"root path does not exist: {candidate}")
    return candidate


def _resolve_environment_root() -> Path | None:
    environment_root = os.getenv(RSRF_ROOT_ENV_VAR)
    if not environment_root:
        return None
    candidate = Path(environment_root).expanduser().resolve()
    if not candidate.exists():
        raise FileNotFoundError(f"{RSRF_ROOT_ENV_VAR} points to a missing path: {candidate}")
    return candidate


def _discover_repo_root_from_directory(current: Path) -> Path | None:
    for candidate in (current, *current.parents):
        if _looks_like_repo_root(candidate):
            return candidate
    return None


def _looks_like_repo_root(candidate: Path) -> bool:
    return (candidate / "pyproject.toml").exists() or (candidate / ".git").exists()


def _package_checkout_root() -> Path | None:
    candidate = Path(__file__).resolve().parents[2]
    if _looks_like_repo_root(candidate):
        return candidate
    return None


def _runtime_release_root() -> Path:
    version = _installed_package_version()
    cache_root = _runtime_release_cache_root(version)
    ready_marker = cache_root / RUNTIME_READY_MARKER_FILENAME
    if ready_marker.exists() and _looks_like_runtime_root(cache_root):
        return cache_root

    if cache_root.exists() and not _looks_like_runtime_root(cache_root):
        shutil.rmtree(cache_root, ignore_errors=True)

    ensure_directory(cache_root.parent)
    staging_root = Path(tempfile.mkdtemp(prefix=f"rsrf_runtime_{version}_", dir=str(cache_root.parent)))
    archive_path = staging_root / "runtime-root.tar.gz"
    extracted_root = staging_root / "extracted"

    try:
        archive_url = _download_runtime_release_archive(version, archive_path)
        _extract_runtime_archive(archive_path, extracted_root)
        runtime_root = _locate_runtime_root(extracted_root)
        if cache_root.exists():
            return cache_root
        shutil.move(str(runtime_root), str(cache_root))
        write_json(
            cache_root / RUNTIME_READY_MARKER_FILENAME,
            {
                "repository": RUNTIME_RELEASE_REPOSITORY,
                "source_url": archive_url,
                "version": version,
            },
        )
        return cache_root
    except Exception as exc:
        raise RuntimeError(
            "RSRF could not locate local repository data and failed to bootstrap the "
            f"matching GitHub release snapshot for version {version}: {exc}"
        ) from exc
    finally:
        shutil.rmtree(staging_root, ignore_errors=True)


def _runtime_release_cache_root(version: str) -> Path:
    return _cache_base_directory() / "rsrf" / "releases" / version


def _cache_base_directory() -> Path:
    override = os.getenv(RSRF_CACHE_DIR_ENV_VAR)
    if override:
        return Path(override).expanduser().resolve()

    home = Path.home()
    if sys.platform == "darwin":
        return (home / "Library" / "Caches").resolve()
    if os.name == "nt":
        local_app_data = os.getenv("LOCALAPPDATA")
        if local_app_data:
            return Path(local_app_data).expanduser().resolve()
        return (home / "AppData" / "Local").resolve()

    xdg_cache_home = os.getenv("XDG_CACHE_HOME")
    if xdg_cache_home:
        return Path(xdg_cache_home).expanduser().resolve()
    return (home / ".cache").resolve()


def _download_runtime_release_archive(version: str, destination: Path) -> str:
    errors: list[str] = []
    for url in _runtime_release_archive_candidates(version):
        try:
            _download_url_to_path(url, destination, version)
            return url
        except (HTTPError, URLError) as exc:
            errors.append(f"{url}: {exc}")
            if destination.exists():
                destination.unlink()
            continue
    raise RuntimeError(" ; ".join(errors) if errors else "no candidate archive URLs were generated")


def _runtime_release_archive_candidates(version: str) -> tuple[str, ...]:
    asset_name = RUNTIME_RELEASE_ASSET_NAME_TEMPLATE.format(version=version)
    return (
        RUNTIME_RELEASE_ASSET_URL_TEMPLATE.format(
            repository=RUNTIME_RELEASE_REPOSITORY,
            version=version,
            asset_name=asset_name,
        ),
        RUNTIME_SOURCE_ARCHIVE_URL_TEMPLATE.format(
            repository=RUNTIME_RELEASE_REPOSITORY,
            version=version,
        ),
        RUNTIME_MAIN_ARCHIVE_URL_TEMPLATE.format(
            repository=RUNTIME_RELEASE_REPOSITORY,
        ),
    )


def _download_url_to_path(url: str, destination: Path, version: str) -> None:
    request = Request(
        url,
        headers={
            "Accept": "application/octet-stream",
            "User-Agent": f"rsrf/{version}",
        },
    )
    ensure_directory(destination.parent)
    with urlopen(request) as response, destination.open("wb") as handle:
        shutil.copyfileobj(response, handle)


def _extract_runtime_archive(archive_path: Path, destination: Path) -> None:
    destination = ensure_directory(destination).resolve()
    with tarfile.open(archive_path, "r:gz") as archive:
        members = archive.getmembers()
        for member in members:
            if member.issym() or member.islnk():
                raise RuntimeError(f"runtime archive contains unsupported link entry: {member.name}")
            member_path = (destination / member.name).resolve()
            try:
                member_path.relative_to(destination)
            except ValueError:
                raise RuntimeError(f"runtime archive contains unsafe path: {member.name}") from None
        archive.extractall(destination)


def _locate_runtime_root(extracted_root: Path) -> Path:
    extracted_root = extracted_root.resolve()
    if _looks_like_runtime_root(extracted_root):
        return extracted_root

    candidates = [child for child in extracted_root.iterdir() if child.is_dir() and _looks_like_runtime_root(child)]
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        raise RuntimeError("runtime archive did not contain data/registry/sensors.parquet")
    raise RuntimeError("runtime archive produced multiple candidate roots")


def _looks_like_runtime_root(candidate: Path) -> bool:
    return (candidate / "data" / "registry" / "sensors.parquet").exists()


def _installed_package_version() -> str:
    package_root = Path(__file__).resolve().parents[2]
    repo_version = _pyproject_version(package_root / "pyproject.toml")
    if repo_version:
        return repo_version

    candidates = [package_root / "src" / "RSRF.egg-info" / "PKG-INFO"]
    candidates.extend(sorted((package_root / "src").glob("RSRF-*.dist-info/METADATA")))
    for candidate in candidates:
        metadata_version = _metadata_version_from_path(candidate)
        if metadata_version:
            return metadata_version

    for distribution_name in ("RSRF", "spectral-response-function"):
        try:
            return distribution_version(distribution_name)
        except PackageNotFoundError:
            continue
    return "0.0.1"


def _metadata_version_from_path(metadata_path: Path) -> str | None:
    if not metadata_path.exists():
        return None
    for line in metadata_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("Version: "):
            return line.split("Version: ", 1)[1].strip()
    return None


def _pyproject_version(pyproject_path: Path) -> str | None:
    if not pyproject_path.exists():
        return None

    in_project_block = False
    for raw_line in pyproject_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line.startswith("["):
            in_project_block = line == "[project]"
            continue
        if in_project_block and line.startswith("version = "):
            version_literal = line.split("=", 1)[1].strip()
            if version_literal.startswith('"') and version_literal.endswith('"'):
                return version_literal[1:-1]
    return None


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
        layout.official_source_manifests_root,
        layout.planning_source_manifests_root,
        layout.template_source_manifests_root,
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
    return layout.canonical_root / content_kind / sensor_unit_id / representation_variant


def realized_variant_dir(
    root: Path | None,
    sensor_unit_id: str,
    representation_variant: str,
) -> Path:
    """Return the realized output directory for a derived sampled-curve variant."""

    layout = build_repo_layout(root)
    return layout.realized_root / sensor_unit_id / representation_variant


def representation_variant_dir(
    root: Path | None,
    *,
    sensor_unit_id: str,
    representation_variant: str,
    content_kind: str,
    realization_kind: str = "none",
) -> Path:
    """Return the storage directory for a sensor representation."""

    if realization_kind != "none":
        return realized_variant_dir(root, sensor_unit_id, representation_variant)
    return canonical_variant_dir(root, content_kind, sensor_unit_id, representation_variant)


def realization_id_from_manifest(manifest: SourceManifest) -> str | None:
    """Build the canonical realization identifier for a manifest."""

    if not manifest.curve_realization.enabled:
        return None
    return (
        f"{manifest.sensor_unit_id}."
        f"{manifest.representation_variant}."
        f"{manifest.curve_realization.output_representation_variant}"
    )


def sensor_row_from_manifest(
    manifest: SourceManifest,
    *,
    representation_variant: str | None = None,
    content_kind: ContentKind | None = None,
    realization_kind: str = "none",
    approximation: bool | None = None,
    status: str = "registered",
) -> dict[str, Any]:
    """Build the canonical sensor registry row for a manifest."""

    band_count = (
        manifest.validation.expected_band_count if isinstance(manifest.validation.expected_band_count, int) else None
    )
    return {
        "sensor_unit_id": manifest.sensor_unit_id,
        "mission_family": manifest.mission_family,
        "platform": manifest.platform,
        "instrument": manifest.instrument,
        "representation_variant": representation_variant or manifest.representation_variant,
        "content_kind": (content_kind or manifest.content_kind).value,
        "realization_kind": realization_kind,
        "spectral_calibration_scope": manifest.canonical.spectral_calibration_scope,
        "spectral_domain": manifest.validation.expected_domain,
        "source_tier": manifest.source_tier.value,
        "approximation": manifest.approximation if approximation is None else approximation,
        "official_source_available": manifest.source_type in {SourceType.OFFICIAL, SourceType.OFFICIAL_METADATA},
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
        manifest.curve_realization.grid_policy.to_dict() if manifest.curve_realization.grid_policy is not None else {}
    )
    truncate_sigma = grid_policy.get("truncate_sigma")
    support_rule = f"center_plus_minus_{truncate_sigma}_sigma" if truncate_sigma is not None else "manifest_defined"
    realization_id = realization_id_from_manifest(manifest)

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
                    "approximate_parametric" if manifest.curve_realization.approximation else "official_parametric"
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
