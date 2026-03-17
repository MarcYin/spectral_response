"""Planning catalog helpers for registry-first sensor backlogs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .io import parquet_support_available, read_json, write_parquet_table
from .models import ContentKind, SourceTier
from .registry import (
    build_repo_layout,
    read_registry_table,
    registry_table_columns,
    registry_table_path,
)


@dataclass(frozen=True)
class PlannedSensorEntry:
    """A planned sensor representation tracked outside the ingest path."""

    sensor_unit_id: str
    representation_variant: str
    content_kind: ContentKind
    spectral_domain: str
    mission_family: str
    platform: str
    instrument: str
    source_tier: SourceTier
    source_url: str
    status: str
    ingest_readiness: str
    blocking_reason: str
    license_note: str
    notes: tuple[str, ...]
    official_source_available: bool = True
    band_count: int | None = None
    approximation: bool = False

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PlannedSensorEntry":
        content_kind = ContentKind(str(payload["content_kind"]))
        source_tier = SourceTier(str(payload["source_tier"]))
        band_count = payload.get("band_count")
        if band_count is not None and not isinstance(band_count, int):
            raise ValueError("planned sensor band_count must be an integer or null")

        notes = payload.get("notes", [])
        if not isinstance(notes, list) or any(not isinstance(item, str) for item in notes):
            raise ValueError("planned sensor notes must be a list of strings")

        return cls(
            sensor_unit_id=str(payload["sensor_unit_id"]),
            representation_variant=str(payload["representation_variant"]),
            content_kind=content_kind,
            spectral_domain=str(payload["spectral_domain"]),
            mission_family=str(payload["mission_family"]),
            platform=str(payload["platform"]),
            instrument=str(payload["instrument"]),
            source_tier=source_tier,
            source_url=str(payload["source_url"]),
            status=str(payload["status"]),
            ingest_readiness=str(payload["ingest_readiness"]),
            blocking_reason=str(payload["blocking_reason"]),
            license_note=str(payload["license_note"]),
            notes=tuple(notes),
            official_source_available=bool(payload.get("official_source_available", True)),
            band_count=band_count,
            approximation=bool(payload.get("approximation", False)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "sensor_unit_id": self.sensor_unit_id,
            "representation_variant": self.representation_variant,
            "content_kind": self.content_kind.value,
            "spectral_domain": self.spectral_domain,
            "mission_family": self.mission_family,
            "platform": self.platform,
            "instrument": self.instrument,
            "source_tier": self.source_tier.value,
            "source_url": self.source_url,
            "status": self.status,
            "ingest_readiness": self.ingest_readiness,
            "blocking_reason": self.blocking_reason,
            "license_note": self.license_note,
            "notes": list(self.notes),
            "official_source_available": self.official_source_available,
            "band_count": self.band_count,
            "approximation": self.approximation,
        }

    def sensor_registry_row(self) -> dict[str, Any]:
        return {
            "sensor_unit_id": self.sensor_unit_id,
            "mission_family": self.mission_family,
            "platform": self.platform,
            "instrument": self.instrument,
            "representation_variant": self.representation_variant,
            "content_kind": self.content_kind.value,
            "realization_kind": "none",
            "spectral_calibration_scope": "sensor_unit",
            "spectral_domain": self.spectral_domain,
            "source_tier": self.source_tier.value,
            "approximation": self.approximation,
            "official_source_available": self.official_source_available,
            "band_count": self.band_count,
            "license_note": self.license_note,
            "status": self.status,
        }


def planned_sensor_catalog_path(root: Path | None = None) -> Path:
    """Return the canonical path for the P2 planned optical catalog."""

    layout = build_repo_layout(root)
    return layout.source_manifests_root / "p2_planned_optical_sensors.json"


def load_planned_sensor_catalog(
    root: Path | None = None,
    *,
    catalog_path: Path | None = None,
) -> dict[str, Any]:
    """Load the planning catalog and return a normalized payload."""

    resolved_path = catalog_path or planned_sensor_catalog_path(root)
    payload = read_json(resolved_path)
    entries_payload = payload.get("entries", [])
    if not isinstance(entries_payload, list):
        raise ValueError("planning catalog entries must be a list")

    entries = [PlannedSensorEntry.from_dict(entry) for entry in entries_payload]
    return {
        "catalog_id": str(payload["catalog_id"]),
        "catalog_version": str(payload["catalog_version"]),
        "bucket": str(payload["bucket"]),
        "entries": entries,
        "path": resolved_path,
    }


def list_planned_sensors(
    root: Path | None = None,
    *,
    catalog_path: Path | None = None,
) -> list[dict[str, Any]]:
    """Return planned sensor entries as JSON-friendly dictionaries."""

    catalog = load_planned_sensor_catalog(root, catalog_path=catalog_path)
    rows = [entry.to_dict() for entry in catalog["entries"]]
    return sorted(rows, key=lambda row: (row["sensor_unit_id"], row["representation_variant"]))


def register_planned_sensor_catalog(
    root: Path | None = None,
    *,
    catalog_path: Path | None = None,
) -> Path | None:
    """Replace the planned slice of the sensor registry with the catalog rows."""

    catalog = load_planned_sensor_catalog(root, catalog_path=catalog_path)
    rows = [entry.sensor_registry_row() for entry in catalog["entries"]]
    if not rows:
        return None
    if not parquet_support_available():
        raise RuntimeError(
            "Parquet support requires either pyarrow or fastparquet in the Python environment"
        )

    try:
        current = read_registry_table(root, "sensors")
    except FileNotFoundError:
        retained_rows: list[dict[str, Any]] = []
    else:
        retained = current[current["status"] != "planned"]
        retained_rows = retained.to_dict(orient="records")

    output_rows = retained_rows + rows
    output_path = registry_table_path(root, "sensors")
    write_parquet_table(
        output_path,
        output_rows,
        columns=registry_table_columns("sensors"),
    )
    return output_path
