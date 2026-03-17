"""Parser for EMIT official OPeNDAP band-parameter ASCII exports."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..band_specs import default_band_id
from ..ingest import ParsedBandSpecArtifacts
from ..io import file_sha256
from ..models import SourceManifest


def parse_emit_band_parameters_ascii(source_path: Path, manifest: SourceManifest) -> ParsedBandSpecArtifacts:
    """Parse EMIT wavelength/FWHM arrays exported through official OPeNDAP ASCII."""

    if not source_path.exists():
        raise FileNotFoundError(f"EMIT ASCII source not found: {source_path}")

    text = source_path.read_text(encoding="utf-8")
    wavelengths = _parse_numeric_series(text, "/sensor_band_parameters/wavelengths,")
    fwhm_values = _parse_numeric_series(text, "/sensor_band_parameters/fwhm,")
    good_wavelengths = [int(value) for value in _parse_numeric_series(text, "/sensor_band_parameters/good_wavelengths,")]
    if not wavelengths or not fwhm_values or not good_wavelengths:
        raise ValueError("EMIT ASCII source must contain wavelengths, fwhm, and good_wavelengths arrays")
    if not (len(wavelengths) == len(fwhm_values) == len(good_wavelengths)):
        raise ValueError("EMIT ASCII arrays must have the same length")

    band_spec_rows: list[dict[str, Any]] = []
    band_rows: list[dict[str, Any]] = []
    for band_index, (wavelength, fwhm_nm, good_flag) in enumerate(
        zip(wavelengths, fwhm_values, good_wavelengths),
        start=1,
    ):
        band_id = default_band_id(band_index)
        band_status = "nominal" if good_flag else "non_science"
        shape_param_json = json.dumps({"good_wavelength": bool(good_flag)}, sort_keys=True)
        band_spec_rows.append(
            {
                "sensor_unit_id": manifest.sensor_unit_id,
                "representation_variant": manifest.representation_variant,
                "band_id": band_id,
                "band_index": band_index,
                "center_wavelength_nm": wavelength,
                "fwhm_nm": fwhm_nm,
                "published_shape_type": manifest.canonical.published_shape_type,
                "shape_param_json": shape_param_json,
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
                "center_wavelength_nm": wavelength,
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
            "module": "rsrf.parsers.emit",
            "function": "parse_emit_band_parameters_ascii",
            "script": manifest.parser.script,
            "entrypoint": manifest.parser.entrypoint,
        },
        "source_artifact": {
            "path": str(source_path),
            "sha256": file_sha256(source_path),
            "size_bytes": source_path.stat().st_size,
        },
        "band_spec_table": {
            "row_count": len(band_spec_rows),
            "monotonic_centers": True,
            "non_science_band_count": sum(1 for value in good_wavelengths if not value),
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


def _parse_numeric_series(text: str, prefix: str) -> list[float]:
    for line in text.splitlines():
        if line.startswith(prefix):
            values = [value.strip() for value in line[len(prefix):].split(",")]
            return [float(value) for value in values if value]
    return []
