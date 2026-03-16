"""Manifest validation and parsing helpers."""

from __future__ import annotations

from json import JSONDecodeError
from pathlib import Path
from typing import Any, Mapping

from .io import read_json
from .models import ManifestValidationError, SourceManifest


def parse_manifest_dict(payload: Mapping[str, Any]) -> SourceManifest:
    """Parse a mapping into a typed source manifest."""

    if not isinstance(payload, Mapping):
        raise ManifestValidationError(["manifest payload must be a JSON object"])
    return SourceManifest.from_dict(payload)


def parse_manifest_file(path: Path) -> SourceManifest:
    """Load and parse a source manifest file."""

    try:
        payload = read_json(path)
    except JSONDecodeError as exc:
        raise ManifestValidationError(
            [f"manifest file is not valid JSON: {exc.msg}"]
        ) from exc
    return parse_manifest_dict(payload)


def validate_manifest_dict(payload: Mapping[str, Any]) -> list[str]:
    """Validate a manifest payload and return a list of errors."""

    try:
        parse_manifest_dict(payload)
    except ManifestValidationError as exc:
        return exc.errors
    return []


def validate_manifest_file(path: Path) -> list[str]:
    """Validate a manifest file and return a list of errors."""

    try:
        parse_manifest_file(path)
    except ManifestValidationError as exc:
        return exc.errors
    return []
