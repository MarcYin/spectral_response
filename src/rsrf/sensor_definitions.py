"""Whole-sensor definition contract and IO helpers."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .io import read_json, read_parquet_table, write_json
from .models import (
    BandDefinition,
    ContentKind,
    SensorDefinition,
    SensorDefinitionValidationError,
)
from .realize import realize_curve
from .registry import read_registry_table, representation_variant_dir
from .response_definitions import (
    response_definition_to_dict,
    validate_response_definition,
)

SENSOR_DEFINITION_SCHEMA_TYPE = "rsrf_sensor_definition"
SENSOR_DEFINITION_SCHEMA_VERSION = "1.0.0"

_ALLOWED_SENSOR_KEYS = {
    "schema_type",
    "schema_version",
    "sensor_id",
    "bands",
    "extensions",
}
_ALLOWED_BAND_KEYS = {
    "band_id",
    "response_definition",
    "extensions",
}
_SPECTRAL_LIBRARY_SEGMENTS = frozenset({"vnir", "swir"})


def sensor_definition_from_dict(payload: Mapping[str, Any]) -> SensorDefinition:
    """Parse and validate a mapping into the stable sensor-definition model."""

    if not isinstance(payload, Mapping):
        raise SensorDefinitionValidationError(["sensor definition payload must be a JSON object"])

    errors: list[str] = []
    _reject_unknown_keys(payload, _ALLOWED_SENSOR_KEYS, "sensor definition", errors)

    schema_type = _required_string(payload, "schema_type", errors, "sensor definition")
    schema_version = _required_string(payload, "schema_version", errors, "sensor definition")
    sensor_id = _required_string(payload, "sensor_id", errors, "sensor definition")

    if schema_type and schema_type != SENSOR_DEFINITION_SCHEMA_TYPE:
        errors.append(f"sensor definition.schema_type must be {SENSOR_DEFINITION_SCHEMA_TYPE!r}, got {schema_type!r}")
    if schema_version and schema_version != SENSOR_DEFINITION_SCHEMA_VERSION:
        errors.append(
            f"sensor definition.schema_version must be {SENSOR_DEFINITION_SCHEMA_VERSION!r}, got {schema_version!r}"
        )

    extensions = _normalize_extensions(
        payload.get("extensions", {}),
        prefix="sensor definition.extensions",
        errors=errors,
        allow_spectral_library=False,
    )

    bands_payload = payload.get("bands")
    if not _is_sequence_like(bands_payload):
        errors.append("sensor definition.bands must be a non-string array")
        bands_payload = []

    band_ids: set[str] = set()
    bands: list[BandDefinition] = []
    for index, band_payload in enumerate(bands_payload):
        prefix = f"sensor definition.bands[{index}]"
        band = _band_definition_from_payload(band_payload, prefix=prefix, errors=errors)
        if band is None:
            continue
        if band.band_id in band_ids:
            errors.append(f"{prefix}.band_id duplicates {band.band_id!r}")
        else:
            band_ids.add(band.band_id)
        bands.append(band)

    if not bands:
        errors.append("sensor definition.bands must contain at least one band")

    if errors:
        raise SensorDefinitionValidationError(errors)

    return SensorDefinition(
        sensor_id=sensor_id,
        bands=tuple(bands),
        schema_type=schema_type,
        schema_version=schema_version,
        extensions=extensions,
    )


def sensor_definition_to_dict(sensor_definition: SensorDefinition) -> dict[str, Any]:
    """Serialize a sensor definition into the stable JSON-facing shape."""

    if not isinstance(sensor_definition, SensorDefinition):
        raise TypeError("sensor_definition must be a SensorDefinition")

    payload = _sensor_definition_payload(sensor_definition)
    normalized = sensor_definition_from_dict(payload)
    return _sensor_definition_payload(normalized)


def load_sensor_definition(source: str | Path, *, root: Path | None = None) -> SensorDefinition:
    """Load a sensor definition from a JSON file."""

    path = _resolve_required_path(source, root=root)
    payload = read_json(path)
    if not isinstance(payload, Mapping):
        raise SensorDefinitionValidationError(["sensor definition payload must be a JSON object"])
    return sensor_definition_from_dict(payload)


def dump_sensor_definition(sensor_definition: SensorDefinition, destination: str | Path) -> None:
    """Write a sensor definition JSON document."""

    payload = sensor_definition_to_dict(sensor_definition)
    write_json(Path(destination).expanduser(), payload)


def coerce_sensor_definition(
    sensor_definition_input: SensorDefinition | Mapping[str, Any] | str | Path,
    *,
    representation_variant: str | None = None,
    root: Path | None = None,
) -> SensorDefinition:
    """Normalize supported inputs into a validated SensorDefinition."""

    if isinstance(sensor_definition_input, SensorDefinition):
        return sensor_definition_from_dict(_sensor_definition_payload(sensor_definition_input))

    if isinstance(sensor_definition_input, Mapping):
        return sensor_definition_from_dict(sensor_definition_input)

    if isinstance(sensor_definition_input, Path):
        return load_sensor_definition(sensor_definition_input, root=root)

    if isinstance(sensor_definition_input, str):
        existing_path = _resolve_existing_path(sensor_definition_input, root=root)
        if existing_path is not None:
            return load_sensor_definition(existing_path, root=root)
        if _looks_like_path(sensor_definition_input):
            raise FileNotFoundError(f"sensor definition file not found: {sensor_definition_input}")
        return get_sensor_definition(
            sensor_definition_input,
            representation_variant=representation_variant,
            root=root,
        )

    raise TypeError("sensor_definition_input must be a SensorDefinition, mapping, path, or sensor id")


def get_sensor_definition(
    sensor_id: str,
    *,
    representation_variant: str | None = None,
    root: Path | None = None,
) -> SensorDefinition:
    """Load a registry-backed sensor definition."""

    sensor_row = _resolve_sensor_variant(sensor_id, representation_variant, root=root)
    resolved_variant = str(sensor_row["representation_variant"])
    content_kind = ContentKind(str(sensor_row["content_kind"]))

    band_rows = _band_rows(sensor_id, resolved_variant, root=root)
    if not band_rows:
        raise KeyError(f"sensor definition bands not found: {sensor_id}/{resolved_variant}")

    bands_payload = _registry_band_payloads(
        sensor_id,
        resolved_variant,
        content_kind=content_kind,
        band_rows=band_rows,
        sensor_row=sensor_row,
        root=root,
    )

    return sensor_definition_from_dict(
        {
            "schema_type": SENSOR_DEFINITION_SCHEMA_TYPE,
            "schema_version": SENSOR_DEFINITION_SCHEMA_VERSION,
            "sensor_id": sensor_id,
            "bands": bands_payload,
            "extensions": {},
        }
    )


def list_sensor_definitions(
    *,
    representation_variant: str | None = None,
    root: Path | None = None,
) -> list[str]:
    """List available registry-backed sensor ids."""

    frame = _available_sensor_rows(root)
    if representation_variant is not None:
        frame = frame[frame["representation_variant"] == representation_variant]
    sensor_ids = {str(row["sensor_unit_id"]) for _, row in frame.iterrows()}
    return sorted(sensor_ids)


def _band_definition_from_payload(
    payload: Any,
    *,
    prefix: str,
    errors: list[str],
) -> BandDefinition | None:
    if not isinstance(payload, Mapping):
        errors.append(f"{prefix} must be an object")
        return None

    _reject_unknown_keys(payload, _ALLOWED_BAND_KEYS, prefix, errors)
    band_id = _required_string(payload, "band_id", errors, prefix)
    response_definition_payload = payload.get("response_definition")
    if not isinstance(response_definition_payload, Mapping):
        errors.append(f"{prefix}.response_definition must be an object")
        response_definition = {}
    else:
        try:
            response_definition = response_definition_to_dict(
                response_definition_payload,
                band_id=band_id or "custom",
                source_variant="custom",
            )
            _validate_realized_response_definition(response_definition, band_id=band_id or "custom")
        except (TypeError, ValueError) as exc:
            errors.append(f"{prefix}.response_definition is invalid: {exc}")
            response_definition = {}

    extensions = _normalize_extensions(
        payload.get("extensions", {}),
        prefix=f"{prefix}.extensions",
        errors=errors,
        allow_spectral_library=True,
    )
    return BandDefinition(
        band_id=band_id,
        response_definition=response_definition,
        extensions=extensions,
    )


def _validate_realized_response_definition(response_definition: Mapping[str, Any], *, band_id: str) -> None:
    resolved = validate_response_definition(
        response_definition,
        band_id=band_id,
        source_variant="custom",
    )
    if hasattr(resolved, "wavelength_nm"):
        return
    realized_curve = realize_curve(resolved)
    validate_response_definition(realized_curve, band_id=band_id, source_variant="custom")


def _normalize_extensions(
    payload: Any,
    *,
    prefix: str,
    errors: list[str],
    allow_spectral_library: bool,
) -> dict[str, Any]:
    if payload is None:
        return {}
    if not isinstance(payload, Mapping):
        errors.append(f"{prefix} must be an object")
        return {}

    normalized: dict[str, Any] = {}
    for namespace, value in payload.items():
        if not isinstance(namespace, str) or not namespace:
            errors.append(f"{prefix} keys must be non-empty strings")
            continue
        if namespace == "spectral_library":
            if not allow_spectral_library:
                errors.append(
                    f"{prefix}.spectral_library is only supported at band level for schema "
                    f"{SENSOR_DEFINITION_SCHEMA_VERSION}"
                )
                continue
            normalized[namespace] = _normalize_spectral_library_extension(
                value,
                prefix=f"{prefix}.spectral_library",
                errors=errors,
            )
            continue
        if not isinstance(value, Mapping):
            errors.append(f"{prefix}.{namespace} must be an object")
            continue
        normalized[namespace] = _normalize_json_mapping(value, prefix=f"{prefix}.{namespace}", errors=errors)
    return normalized


def _normalize_spectral_library_extension(
    payload: Any,
    *,
    prefix: str,
    errors: list[str],
) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        errors.append(f"{prefix} must be an object")
        return {}

    allowed_keys = {"segment"}
    _reject_unknown_keys(payload, allowed_keys, prefix, errors)
    segment = _required_string(payload, "segment", errors, prefix)
    if segment and segment not in _SPECTRAL_LIBRARY_SEGMENTS:
        errors.append(f"{prefix}.segment must be one of {sorted(_SPECTRAL_LIBRARY_SEGMENTS)!r}")
    return {"segment": segment} if segment else {}


def _normalize_json_mapping(
    payload: Mapping[str, Any],
    *,
    prefix: str,
    errors: list[str],
) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key, value in payload.items():
        if not isinstance(key, str) or not key:
            errors.append(f"{prefix} keys must be non-empty strings")
            continue
        normalized[key] = _normalize_json_value(value, prefix=f"{prefix}.{key}", errors=errors)
    return normalized


def _normalize_json_value(value: Any, *, prefix: str, errors: list[str]) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            errors.append(f"{prefix} must be finite")
        return value
    if isinstance(value, Mapping):
        return _normalize_json_mapping(value, prefix=prefix, errors=errors)
    if _is_sequence_like(value):
        return [_normalize_json_value(item, prefix=prefix, errors=errors) for item in value]
    errors.append(f"{prefix} contains unsupported value of type {type(value).__name__}")
    return None


def _sensor_definition_payload(sensor_definition: SensorDefinition) -> dict[str, Any]:
    return {
        "schema_type": sensor_definition.schema_type,
        "schema_version": sensor_definition.schema_version,
        "sensor_id": sensor_definition.sensor_id,
        "bands": [
            {
                "band_id": band.band_id,
                "response_definition": _clone_json_value(band.response_definition),
                "extensions": _clone_json_value(band.extensions),
            }
            for band in sensor_definition.bands
        ],
        "extensions": _clone_json_value(sensor_definition.extensions),
    }


def _clone_json_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _clone_json_value(item) for key, item in value.items()}
    if _is_sequence_like(value):
        return [_clone_json_value(item) for item in value]
    return value


def _available_sensor_rows(root: Path | None):
    frame = read_registry_table(root, "sensors")
    mask = frame.apply(_row_has_backing_artifact, axis=1, root=root)
    return frame[mask].copy()


def _resolve_sensor_variant(
    sensor_id: str,
    representation_variant: str | None,
    *,
    root: Path | None = None,
):
    frame = _available_sensor_rows(root)
    frame = frame[frame["sensor_unit_id"] == sensor_id]
    if representation_variant is not None:
        frame = frame[frame["representation_variant"] == representation_variant]
    if frame.empty:
        raise KeyError(f"sensor definition not found: {sensor_id}/{representation_variant}")
    if len(frame) > 1:
        raise ValueError(f"multiple sensor definitions found for {sensor_id}; representation_variant is required")
    return frame.iloc[0]


def _row_has_backing_artifact(row, *, root: Path | None) -> bool:
    content_kind = ContentKind(str(row["content_kind"]))
    artifact_name = "curves.parquet" if content_kind == ContentKind.SAMPLED_CURVE else "band_specs.parquet"
    artifact_path = (
        representation_variant_dir(
            root,
            sensor_unit_id=str(row["sensor_unit_id"]),
            representation_variant=str(row["representation_variant"]),
            content_kind=str(row["content_kind"]),
            realization_kind=str(row.get("realization_kind", "none")),
        )
        / artifact_name
    )
    return artifact_path.exists()


def _band_rows(sensor_id: str, representation_variant: str, *, root: Path | None = None) -> list[dict[str, Any]]:
    frame = read_registry_table(root, "bands")
    frame = frame[(frame["sensor_unit_id"] == sensor_id) & (frame["representation_variant"] == representation_variant)]
    if "band_index" in frame.columns:
        frame = frame.sort_values(["band_index", "band_id"], na_position="last")
    else:
        frame = frame.sort_values(["band_id"])
    return frame.to_dict(orient="records")


def _registry_band_payloads(
    sensor_id: str,
    representation_variant: str,
    *,
    content_kind: ContentKind,
    band_rows: list[dict[str, Any]],
    sensor_row,
    root: Path | None,
) -> list[dict[str, Any]]:
    representation_dir = representation_variant_dir(
        root,
        sensor_unit_id=sensor_id,
        representation_variant=representation_variant,
        content_kind=content_kind.value,
        realization_kind=str(sensor_row.get("realization_kind", "none")),
    )

    if content_kind == ContentKind.SAMPLED_CURVE:
        frame = read_parquet_table(representation_dir / "curves.parquet")
        frame = frame[
            (frame["sensor_unit_id"] == sensor_id) & (frame["representation_variant"] == representation_variant)
        ]
        frame = frame.sort_values(["band_id", "wavelength_nm"])
        return [
            {
                "band_id": str(band_row["band_id"]),
                "response_definition": response_definition_to_dict(
                    {
                        "kind": "sampled",
                        "wavelength_nm": _band_curve_samples(frame, str(band_row["band_id"]), "wavelength_nm"),
                        "response": _band_curve_samples(frame, str(band_row["band_id"]), "response"),
                    },
                    band_id=str(band_row["band_id"]),
                    source_variant=representation_variant,
                ),
                "extensions": _registry_band_extensions(),
            }
            for band_row in band_rows
        ]

    if content_kind == ContentKind.BAND_SPEC:
        frame = read_parquet_table(representation_dir / "band_specs.parquet")
        frame = frame[
            (frame["sensor_unit_id"] == sensor_id) & (frame["representation_variant"] == representation_variant)
        ]
        rows_by_band = {str(row["band_id"]): row for _, row in frame.iterrows()}
        payloads: list[dict[str, Any]] = []
        for band_row in band_rows:
            band_id = str(band_row["band_id"])
            artifact_row = rows_by_band.get(band_id)
            if artifact_row is None:
                raise KeyError(f"band spec not found for {sensor_id}/{representation_variant}/{band_id}")
            payloads.append(
                {
                    "band_id": band_id,
                    "response_definition": response_definition_to_dict(
                        {
                            "kind": "gaussian",
                            "center_wavelength_nm": float(artifact_row["center_wavelength_nm"]),
                            "fwhm_nm": float(artifact_row["fwhm_nm"]),
                        },
                        band_id=band_id,
                        source_variant=representation_variant,
                    ),
                    "extensions": _registry_band_extensions(),
                }
            )
        return payloads

    raise NotImplementedError(f"content_kind not supported for sensor definitions: {content_kind.value}")


def _band_curve_samples(frame, band_id: str, column_name: str) -> list[float]:
    band_frame = frame[frame["band_id"] == band_id]
    if band_frame.empty:
        raise KeyError(f"sampled curve not found for band {band_id}")
    return [float(value) for value in band_frame[column_name].tolist()]


def _registry_band_extensions() -> dict[str, Any]:
    return {}


def _resolve_required_path(source: str | Path, *, root: Path | None = None) -> Path:
    existing_path = _resolve_existing_path(source, root=root)
    if existing_path is None:
        raise FileNotFoundError(f"sensor definition file not found: {source}")
    return existing_path


def _resolve_existing_path(source: str | Path, *, root: Path | None = None) -> Path | None:
    path = Path(source).expanduser()
    candidates = [path]
    if not path.is_absolute() and root is not None:
        candidates.append(Path(root).expanduser() / path)
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    return None


def _looks_like_path(value: str) -> bool:
    return value.endswith(".json") or "/" in value or "\\" in value


def _required_string(
    payload: Mapping[str, Any],
    key: str,
    errors: list[str],
    prefix: str,
) -> str:
    value = payload.get(key)
    if value is None:
        errors.append(f"{prefix}.{key} is required")
        return ""
    if not isinstance(value, str):
        errors.append(f"{prefix}.{key} must be a string")
        return ""
    if not value.strip():
        errors.append(f"{prefix}.{key} must be non-empty")
        return ""
    return value


def _reject_unknown_keys(
    payload: Mapping[str, Any],
    allowed_keys: set[str],
    prefix: str,
    errors: list[str],
) -> None:
    for key in payload:
        if key not in allowed_keys:
            errors.append(f"{prefix} contains unsupported field {key!r}")


def _is_sequence_like(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))
