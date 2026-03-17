"""Parser for multi-band sampled-curve CSV tables."""

from __future__ import annotations

import csv
import re
from pathlib import Path

from ..models import SourceManifest
from .common import ParsedBandCurve, build_sampled_curve_artifacts

_WAVELENGTH_FIELD_RE = re.compile(r"(wavelength|\bwl\b)", re.IGNORECASE)
_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


def parse_multiband_curve_csv(csv_path: Path, manifest: SourceManifest):
    """Parse a CSV with one wavelength column and one response column per band."""

    if not csv_path.exists():
        raise FileNotFoundError(f"curve CSV not found: {csv_path}")

    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError(f"curve CSV does not contain a header row: {csv_path}")

        wavelength_field = _resolve_wavelength_field(reader.fieldnames)
        band_fields = [field for field in reader.fieldnames if field != wavelength_field]
        if not band_fields:
            raise ValueError(f"curve CSV does not contain any band columns: {csv_path}")

        wavelength_nm: list[float] = []
        per_band_response: dict[str, list[float]] = {field: [] for field in band_fields}
        for row in reader:
            wavelength_nm.append(_parse_wavelength_nm(row[wavelength_field], wavelength_field))
            for field in band_fields:
                per_band_response[field].append(_parse_response_value(row.get(field)))

    parsed_bands: list[ParsedBandCurve] = []
    for order_index, field in enumerate(band_fields, start=1):
        band_id = _normalize_band_id(field)
        parsed_bands.append(
            ParsedBandCurve(
                band_id=band_id,
                band_index=order_index,
                band_name=band_id,
                wavelength_nm=wavelength_nm,
                response=per_band_response[field],
            )
        )

    return build_sampled_curve_artifacts(
        manifest,
        csv_path,
        parsed_bands,
        parser_module="rsrf.parsers.multiband_curve_csv",
        parser_function="parse_multiband_curve_csv",
        extra_metadata={
            "curve_csv": {
                "wavelength_field": wavelength_field,
                "band_fields": band_fields,
            }
        },
    )


def _resolve_wavelength_field(fieldnames: list[str]) -> str:
    for field in fieldnames:
        if _WAVELENGTH_FIELD_RE.search(field):
            return field
    raise ValueError(f"unable to locate wavelength column in header: {fieldnames!r}")


def _parse_wavelength_nm(value: str | None, field_name: str) -> float:
    if value in ("", None):
        raise ValueError(f"missing wavelength value in {field_name}")
    wavelength = float(value)
    normalized = field_name.lower()
    if "um" in normalized or "µm" in normalized:
        return wavelength * 1000.0
    return wavelength if wavelength > 100.0 else wavelength * 1000.0


def _parse_response_value(value: str | None) -> float:
    if value in ("", None):
        return 0.0
    return float(value)


def _normalize_band_id(field_name: str) -> str:
    normalized = field_name.lower()
    normalized = normalized.replace("response", "")
    normalized = normalized.replace("near infrared", "nir")
    normalized = normalized.replace("near-infrared", "nir")
    normalized = normalized.replace("near ir", "nir")
    normalized = normalized.replace("coastal blue", "coastalblue")
    normalized = normalized.replace("red edge", "rededge")
    normalized = normalized.replace("green i", "greeni")
    normalized = normalized.replace("green ii", "greenii")
    token = _NON_ALNUM_RE.sub("", normalized)

    band_ids = {
        "blue": "Blue",
        "green": "Green",
        "red": "Red",
        "nir": "NIR",
        "pan": "Pan",
        "panchromatic": "Pan",
        "coastalblue": "CoastalBlue",
        "greeni": "GreenI",
        "greenii": "GreenII",
        "yellow": "Yellow",
        "rededge": "RedEdge",
    }
    if token not in band_ids:
        raise ValueError(f"unsupported band column name: {field_name!r}")
    return band_ids[token]
