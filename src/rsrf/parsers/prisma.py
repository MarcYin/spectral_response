"""Parser for official PRISMA HE5 product metadata."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..band_specs import default_band_id
from ..ingest import ParsedBandSpecArtifacts
from ..io import file_sha256
from ..models import SourceManifest

_SUBSYSTEM_SPECS = (
    ("VNIR", "List_Cw_Vnir", "List_Fwhm_Vnir"),
    ("SWIR", "List_Cw_Swir", "List_Fwhm_Swir"),
)


def parse_prisma_he5_metadata(source_path: Path, manifest: SourceManifest) -> ParsedBandSpecArtifacts:
    """Parse exact band centers and FWHM arrays from an official PRISMA granule."""

    if not source_path.exists():
        raise FileNotFoundError(f"PRISMA source not found: {source_path}")

    try:
        import h5py
    except ImportError as exc:
        raise RuntimeError("h5py is required to parse PRISMA HE5 metadata") from exc

    with h5py.File(source_path, "r") as handle:
        product_id = _decode_scalar(handle.attrs.get("Product_ID"))
        product_name = _decode_scalar(handle.attrs.get("Product_Name"))
        processing_level = _decode_scalar(handle.attrs.get("Processing_Level"))
        image_id = _decode_scalar(handle.attrs.get("Image_ID"))

        band_spec_rows: list[dict[str, Any]] = []
        band_rows: list[dict[str, Any]] = []
        dropped_slots: dict[str, int] = {}
        subsystem_counts: dict[str, int] = {}
        band_index = 1

        for subsystem, center_key, fwhm_key in _SUBSYSTEM_SPECS:
            if center_key not in handle.attrs or fwhm_key not in handle.attrs:
                raise ValueError(
                    f"PRISMA HE5 source must contain {center_key} and {fwhm_key} attributes"
                )
            centers = list(handle.attrs[center_key])
            fwhm_values = list(handle.attrs[fwhm_key])
            if len(centers) != len(fwhm_values):
                raise ValueError(
                    f"PRISMA metadata arrays {center_key} and {fwhm_key} must have the same length"
                )

            subsystem_valid = 0
            subsystem_dropped = 0
            for slot_index, (center_raw, fwhm_raw) in enumerate(zip(centers, fwhm_values), start=1):
                center_wavelength_nm = float(center_raw)
                fwhm_nm = float(fwhm_raw)
                if center_wavelength_nm <= 0 or fwhm_nm <= 0:
                    subsystem_dropped += 1
                    continue

                band_id = default_band_id(band_index)
                band_name = f"{subsystem}{slot_index:03d}"
                shape_param_json = json.dumps(
                    {
                        "subsystem": subsystem,
                        "subsystem_band_index": slot_index,
                        "product_level": processing_level,
                    },
                    sort_keys=True,
                )
                band_spec_rows.append(
                    {
                        "sensor_unit_id": manifest.sensor_unit_id,
                        "representation_variant": manifest.representation_variant,
                        "band_id": band_id,
                        "band_index": band_index,
                        "center_wavelength_nm": center_wavelength_nm,
                        "fwhm_nm": fwhm_nm,
                        "published_shape_type": manifest.canonical.published_shape_type,
                        "shape_param_json": shape_param_json,
                        "band_status": "nominal",
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
                        "band_name": band_name,
                        "center_wavelength_nm": center_wavelength_nm,
                        "fwhm_nm": fwhm_nm,
                        "published_shape_type": manifest.canonical.published_shape_type,
                        "band_status": "nominal",
                        "native_support_min_nm": None,
                        "native_support_max_nm": None,
                        "native_sampling_nm": None,
                        "normalization": manifest.canonical.normalization,
                        "has_sampled_curve": False,
                        "has_band_spec": True,
                    }
                )
                subsystem_valid += 1
                band_index += 1

            subsystem_counts[subsystem] = subsystem_valid
            dropped_slots[subsystem] = subsystem_dropped

    centers = [row["center_wavelength_nm"] for row in band_spec_rows]
    monotonic_centers = all(
        current > previous for previous, current in zip(centers, centers[1:])
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
            "module": "rsrf.parsers.prisma",
            "function": "parse_prisma_he5_metadata",
            "script": manifest.parser.script,
            "entrypoint": manifest.parser.entrypoint,
        },
        "source_artifact": {
            "path": str(source_path),
            "sha256": file_sha256(source_path),
            "size_bytes": source_path.stat().st_size,
        },
        "product_metadata": {
            "product_id": product_id,
            "product_name": product_name,
            "processing_level": processing_level,
            "image_id": image_id,
        },
        "band_spec_table": {
            "row_count": len(band_spec_rows),
            "monotonic_centers": monotonic_centers,
            "subsystem_counts": subsystem_counts,
            "dropped_invalid_slots": dropped_slots,
            "ordering_policy": "vnir_then_swir_native_slot_order",
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


def _decode_scalar(value: Any) -> Any:
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return value
