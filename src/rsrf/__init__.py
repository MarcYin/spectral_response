"""Bootstrap package for the spectral response function repository."""

from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent

try:
    __version__ = version("spectral-response-function")
except PackageNotFoundError:
    __version__ = "0.1.0"

__all__ = ["PACKAGE_ROOT", "__version__"]
