"""Parsers for NASA OBPG RSR netCDF and bandpass table sources."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import xarray as xr

from ..ingest import ParsedBandSpecArtifacts
from ..io import file_sha256
from ..models import SourceManifest
from .common import ParsedBandCurve, build_sampled_curve_artifacts


def parse_obpg_rsr_netcdf(netcdf_path: Path, manifest: SourceManifest):
    """Parse a NASA OBPG RSR netCDF file with shared wavelength and band axes."""

    if not netcdf_path.exists():
        raise FileNotFoundError(f"netCDF file not found: {netcdf_path}")

    dataset = xr.open_dataset(netcdf_path, engine="netcdf4")
    try:
        if "wavelength" not in dataset or "RSR" not in dataset:
            raise ValueError("OBPG RSR netCDF must contain 'wavelength' and 'RSR' variables")
        if "bands" not in dataset.coords:
            raise ValueError("OBPG RSR netCDF must expose a 'bands' coordinate")

        wavelength_nm = np.asarray(dataset["wavelength"].values, dtype=float)
        response_array = np.asarray(dataset["RSR"].values, dtype=float)
        band_centers = np.asarray(dataset["bands"].values, dtype=float)

        if wavelength_nm.ndim != 1:
            raise ValueError("OBPG wavelength axis must be one-dimensional")
        if response_array.ndim != 2:
            raise ValueError("OBPG RSR variable must be two-dimensional")
        if response_array.shape != (band_centers.size, wavelength_nm.size):
            raise ValueError("OBPG RSR dimensions do not match wavelength/band coordinates")

        negative_values_clipped = 0
        parsed_bands: list[ParsedBandCurve] = []
        band_count = int(band_centers.size)
        for band_offset in range(band_count):
            response = np.asarray(response_array[band_offset], dtype=float)
            valid_mask = np.isfinite(wavelength_nm) & np.isfinite(response)
            if not np.any(valid_mask):
                raise ValueError(f"band {band_offset + 1} does not contain any finite samples")

            band_wavelengths = wavelength_nm[valid_mask]
            band_response = response[valid_mask]
            negative_mask = band_response < 0.0
            if np.any(negative_mask):
                negative_values_clipped += int(np.count_nonzero(negative_mask))
                band_response = band_response.copy()
                band_response[negative_mask] = 0.0

            band_id = _obpg_band_id(band_offset + 1, band_count)
            parsed_bands.append(
                ParsedBandCurve(
                    band_id=band_id,
                    band_index=band_offset + 1,
                    band_name=f"{float(band_centers[band_offset]):g} nm",
                    wavelength_nm=band_wavelengths.tolist(),
                    response=band_response.tolist(),
                )
            )
    finally:
        dataset.close()

    artifacts = build_sampled_curve_artifacts(
        manifest,
        netcdf_path,
        parsed_bands,
        parser_module="rsrf.parsers.obpg",
        parser_function="parse_obpg_rsr_netcdf",
        extra_metadata={
            "obpg_rsr": {
                "band_coordinate_units": "nm",
                "band_coordinate_count": band_count,
                "negative_values_clipped": negative_values_clipped,
            }
        },
    )
    for band_row, band_center in zip(artifacts.band_rows, band_centers.tolist()):
        band_row["center_wavelength_nm"] = float(band_center)
    return artifacts


def parse_obpg_bandpass_csv(table_path: Path, manifest: SourceManifest) -> ParsedBandSpecArtifacts:
    """Parse an OBPG bandpass summary CSV into canonical band-spec rows."""

    if not table_path.exists():
        raise FileNotFoundError(f"bandpass table not found: {table_path}")

    mapping = manifest.band_spec
    if not mapping.band_index_field or not mapping.center_wavelength_field or not mapping.fwhm_field:
        raise ValueError(
            "OBPG bandpass manifests must declare band_index_field, center_wavelength_field, and fwhm_field"
        )

    records = _load_obpg_bandpass_rows(table_path, mapping.band_index_field)
    if not records:
        raise ValueError("bandpass table is empty")

    band_spec_rows: list[dict[str, Any]] = []
    band_rows: list[dict[str, Any]] = []
    for record in records:
        band_index = int(float(str(record[mapping.band_index_field]).strip()))
        band_id = (
            str(record[mapping.band_id_field]).strip()
            if mapping.band_id_field and str(record.get(mapping.band_id_field, "")).strip()
            else _obpg_band_id(band_index, len(records))
        )
        center_wavelength_nm = float(str(record[mapping.center_wavelength_field]).strip())
        fwhm_nm = float(str(record[mapping.fwhm_field]).strip())
        band_status = (
            str(record[mapping.band_status_field]).strip()
            if mapping.band_status_field and str(record.get(mapping.band_status_field, "")).strip()
            else "nominal"
        )
        shape_param_json = {
            param_name: record[field_name]
            for param_name, field_name in mapping.shape_param_fields.items()
            if field_name in record and str(record[field_name]).strip()
        }

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
                "band_name": f"{center_wavelength_nm:g} nm",
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
            "module": "rsrf.parsers.obpg",
            "function": "parse_obpg_bandpass_csv",
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
            "monotonic_centers": _centers_are_monotonic(band_spec_rows),
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


def _load_obpg_bandpass_rows(table_path: Path, band_index_field: str) -> list[dict[str, str]]:
    with table_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, skipinitialspace=True)
        rows: list[dict[str, str]] = []
        for row in reader:
            if not any(str(value).strip() for value in row.values() if value is not None):
                continue
            band_index_value = str(row.get(band_index_field, "")).strip()
            if not band_index_value:
                continue
            rows.append({str(key): "" if value is None else str(value) for key, value in row.items()})
    return rows


def _centers_are_monotonic(rows: list[dict[str, Any]]) -> bool:
    centers = [float(row["center_wavelength_nm"]) for row in rows]
    return len(centers) < 2 or all(current < following for current, following in zip(centers, centers[1:]))


def _obpg_band_id(band_index: int, band_count: int) -> str:
    width = max(2, len(str(int(band_count))))
    return f"B{band_index:0{width}d}"
