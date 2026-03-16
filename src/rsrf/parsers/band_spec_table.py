"""Generic parser for metadata-only band-spec tables."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..band_specs import default_band_id
from ..ingest import ParsedBandSpecArtifacts
from ..io import file_sha256, read_json
from ..models import SourceManifest


def parse_band_spec_table(table_path: Path, manifest: SourceManifest) -> ParsedBandSpecArtifacts:
    """Parse a CSV or JSON band-spec table according to the manifest field mapping."""

    if not table_path.exists():
        raise FileNotFoundError(f"band-spec table not found: {table_path}")

    records = _load_table_records(table_path)
    if not records:
        raise ValueError("band-spec table is empty")

    mapping = manifest.band_spec
    if not mapping.center_wavelength_field or not mapping.fwhm_field:
        raise ValueError("band-spec manifest must declare center_wavelength_field and fwhm_field")

    band_spec_rows: list[dict[str, Any]] = []
    band_rows: list[dict[str, Any]] = []
    band_statuses: dict[str, str] = {}
    centers: list[float] = []

    for record in records:
        band_index = _optional_int(record, mapping.band_index_field)
        band_id = _resolve_band_id(record, mapping.band_id_field, band_index)
        center_wavelength_nm = _required_float(record, mapping.center_wavelength_field)
        fwhm_nm = _required_float(record, mapping.fwhm_field)
        band_status = _optional_string(record, mapping.band_status_field) or "nominal"
        shape_param_json = {
            param_name: record[field_name]
            for param_name, field_name in mapping.shape_param_fields.items()
            if field_name in record and record[field_name] not in ("", None)
        }

        centers.append(center_wavelength_nm)
        band_statuses[band_id] = band_status
        band_spec_rows.append(
            {
                "sensor_unit_id": manifest.sensor_unit_id,
                "representation_variant": manifest.representation_variant,
                "band_id": band_id,
                "band_index": band_index,
                "center_wavelength_nm": center_wavelength_nm,
                "fwhm_nm": fwhm_nm,
                "published_shape_type": manifest.canonical.published_shape_type,
                "shape_param_json": json.dumps(shape_param_json, sort_keys=True),
                "band_status": band_status,
                "is_official": True,
                "source_id": manifest.source_id,
            }
        )
        band_rows.append(
            {
                "sensor_unit_id": manifest.sensor_unit_id,
                "representation_variant": manifest.representation_variant,
                "band_id": band_id,
                "band_index": band_index,
                "band_name": band_id,
                "center_wavelength_nm": center_wavelength_nm,
                "fwhm_nm": fwhm_nm,
                "published_shape_type": manifest.canonical.published_shape_type,
                "band_status": band_status,
                "native_support_min_nm": None,
                "native_support_max_nm": None,
                "native_sampling_nm": None,
                "normalization": manifest.canonical.normalization,
                "has_sampled_curve": False,
                "has_band_spec": True,
            }
        )

    metadata = {
        "source_id": manifest.source_id,
        "sensor_unit_id": manifest.sensor_unit_id,
        "representation_variant": manifest.representation_variant,
        "content_kind": manifest.content_kind.value,
        "source_tier": manifest.source_tier.value,
        "source_type": manifest.source_type.value,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "parser": {
            "module": "rsrf.parsers.band_spec_table",
            "function": "parse_band_spec_table",
            "script": manifest.parser.script,
            "entrypoint": manifest.parser.entrypoint,
        },
        "source_artifact": {
            "path": str(table_path),
            "sha256": file_sha256(table_path),
            "size_bytes": table_path.stat().st_size,
        },
        "band_spec_table": {
            "row_count": len(band_spec_rows),
            "monotonic_centers": centers == sorted(centers),
            "status_counts": _status_counts(band_statuses),
        },
        "field_mapping": manifest.band_spec.to_dict(),
        "realization": manifest.curve_realization.to_dict(),
        "manifest": manifest.to_dict(),
    }

    return ParsedBandSpecArtifacts(
        band_spec_rows=band_spec_rows,
        band_rows=band_rows,
        metadata=metadata,
    )


def _load_table_records(table_path: Path) -> list[dict[str, Any]]:
    suffix = table_path.suffix.lower()
    if suffix == ".csv":
        with table_path.open("r", encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))
    if suffix == ".json":
        payload = read_json(table_path)
        if isinstance(payload, list):
            return [dict(item) for item in payload]
        if isinstance(payload, dict) and isinstance(payload.get("records"), list):
            return [dict(item) for item in payload["records"]]
        raise ValueError("JSON band-spec tables must be a list or contain a 'records' list")
    raise ValueError(f"unsupported band-spec table format: {table_path.suffix}")


def _resolve_band_id(record: dict[str, Any], band_id_field: str | None, band_index: int | None) -> str:
    if band_id_field and record.get(band_id_field):
        return str(record[band_id_field]).strip()
    if band_index is None:
        raise ValueError("band-spec record is missing both band_id and band_index")
    return default_band_id(band_index)


def _required_float(record: dict[str, Any], field_name: str) -> float:
    if field_name not in record or record[field_name] in ("", None):
        raise ValueError(f"missing required field: {field_name}")
    return float(record[field_name])


def _optional_int(record: dict[str, Any], field_name: str | None) -> int | None:
    if not field_name or field_name not in record or record[field_name] in ("", None):
        return None
    return int(record[field_name])


def _optional_string(record: dict[str, Any], field_name: str | None) -> str | None:
    if not field_name or field_name not in record:
        return None
    value = record[field_name]
    if value in ("", None):
        return None
    return str(value)


def _status_counts(statuses: dict[str, str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for status in statuses.values():
        counts[status] = counts.get(status, 0) + 1
    return counts
