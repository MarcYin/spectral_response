"""Bootstrap package for the spectral response function repository."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from .api import (
    get_metadata,
    get_sensor_definition,
    list_bands,
    list_sensor_definitions,
    list_sensors,
    load_band_spec,
    load_curve,
    load_response_definition,
)
from .docs_site import prepare_docs_site
from .manifests import iter_source_manifest_paths, manifest_path, resolve_manifest_path
from .planning import list_planned_sensors, register_planned_sensor_catalog
from .qa import validate_sampled_curve_inventory, validate_sensor, write_validation_artifacts
from .realize import realize_curve
from .response_definitions import coerce_response_definition
from .sensor_definitions import (
    BandDefinition,
    SensorDefinition,
    SensorDefinitionValidationError,
    coerce_sensor_definition,
    dump_sensor_definition,
    load_sensor_definition,
    sensor_definition_from_dict,
    sensor_definition_to_dict,
)
from .visualization import export_docs_visualization_assets

PACKAGE_ROOT = Path(__file__).resolve().parent


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


def _local_distribution_version() -> str | None:
    repo_version = _pyproject_version(PACKAGE_ROOT.parent.parent / "pyproject.toml")
    if repo_version:
        return repo_version

    candidates = [PACKAGE_ROOT.parent / "RSRF.egg-info" / "PKG-INFO"]
    candidates.extend(sorted(PACKAGE_ROOT.parent.glob("RSRF-*.dist-info/METADATA")))
    for candidate in candidates:
        local_version = _metadata_version_from_path(candidate)
        if local_version:
            return local_version
    return None


_local_version = _local_distribution_version()
if _local_version:
    __version__ = _local_version
else:
    __version__ = "0.0.1"
    for _distribution_name in ("RSRF", "spectral-response-function"):
        try:
            __version__ = version(_distribution_name)
            break
        except PackageNotFoundError:
            continue

__all__ = [
    "PACKAGE_ROOT",
    "BandDefinition",
    "SensorDefinition",
    "SensorDefinitionValidationError",
    "__version__",
    "coerce_response_definition",
    "coerce_sensor_definition",
    "dump_sensor_definition",
    "export_docs_visualization_assets",
    "get_metadata",
    "get_sensor_definition",
    "iter_source_manifest_paths",
    "list_bands",
    "list_planned_sensors",
    "list_sensor_definitions",
    "list_sensors",
    "load_band_spec",
    "load_curve",
    "load_response_definition",
    "load_sensor_definition",
    "manifest_path",
    "prepare_docs_site",
    "realize_curve",
    "register_planned_sensor_catalog",
    "resolve_manifest_path",
    "sensor_definition_from_dict",
    "sensor_definition_to_dict",
    "validate_sampled_curve_inventory",
    "validate_sensor",
    "write_validation_artifacts",
]
