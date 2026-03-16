"""Bootstrap package for the spectral response function repository."""

from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from .api import get_metadata, list_bands, list_sensors, load_band_spec, load_curve, load_response_definition

PACKAGE_ROOT = Path(__file__).resolve().parent

try:
    __version__ = version("spectral-response-function")
except PackageNotFoundError:
    __version__ = "0.1.0"

__all__ = [
    "PACKAGE_ROOT",
    "__version__",
    "get_metadata",
    "list_bands",
    "list_sensors",
    "load_band_spec",
    "load_curve",
    "load_response_definition",
]
