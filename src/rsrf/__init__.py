"""Bootstrap package for the spectral response function repository."""

from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from .api import get_metadata, list_bands, list_sensors, load_band_spec, load_curve, load_response_definition
from .manifests import iter_source_manifest_paths, manifest_path, resolve_manifest_path
from .planning import list_planned_sensors, register_planned_sensor_catalog
from .qa import validate_sensor, write_validation_artifacts
from .realize import realize_curve

PACKAGE_ROOT = Path(__file__).resolve().parent

for _distribution_name in ("RSRF", "spectral-response-function"):
    try:
        __version__ = version(_distribution_name)
        break
    except PackageNotFoundError:
        continue
else:
    __version__ = "0.1.0"

__all__ = [
    "PACKAGE_ROOT",
    "__version__",
    "get_metadata",
    "iter_source_manifest_paths",
    "list_bands",
    "list_planned_sensors",
    "list_sensors",
    "load_band_spec",
    "load_curve",
    "load_response_definition",
    "manifest_path",
    "realize_curve",
    "resolve_manifest_path",
    "register_planned_sensor_catalog",
    "validate_sensor",
    "write_validation_artifacts",
]
