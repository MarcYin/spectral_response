"""Parser for USGS Spectral Characteristics Viewer per-band JSON exports."""

from __future__ import annotations

import json
import re
from pathlib import Path

from ..models import SourceManifest
from .common import ParsedBandCurve, build_sampled_curve_artifacts

_LANDSAT_RE = re.compile(
    r"^Landsat(?P<platform>\d)(?P<instrument>MSS|TM|ETM\+|OLI|TIRS)(?P<band>thermal\d+|\d+pan|\d+)$"
)
_ASTER_RE = re.compile(r"^TerraASTER(?P<band>thermal\d+|\d+[BN]?)$")


def parse_usgs_json_directory(source_dir: Path, manifest: SourceManifest):
    """Parse a directory of USGS SCV per-band JSON files."""

    if not source_dir.exists():
        raise FileNotFoundError(f"source directory not found: {source_dir}")
    if not source_dir.is_dir():
        raise ValueError(f"USGS JSON parser requires a directory path: {source_dir}")

    band_files = sorted(source_dir.glob("*.json"))
    if not band_files:
        raise ValueError(f"no JSON band files found in directory: {source_dir}")

    parsed_bands: list[ParsedBandCurve] = []
    for band_file in band_files:
        band_id, band_index, band_name = _parse_usgs_band_identity(
            band_file.stem,
            sensor_unit_id=manifest.sensor_unit_id,
        )
        payload = json.loads(band_file.read_text(encoding="utf-8"))
        if not isinstance(payload, list) or not payload:
            raise ValueError(f"unexpected JSON payload for {band_file.name}")
        wavelength_nm, response = _extract_usgs_curve_arrays(payload, band_file.name)
        parsed_bands.append(
            ParsedBandCurve(
                band_id=band_id,
                band_index=band_index,
                band_name=band_name,
                wavelength_nm=wavelength_nm,
                response=response,
            )
        )

    parsed_bands.sort(key=lambda band: (band.band_index or 0, band.band_id))
    return build_sampled_curve_artifacts(
        manifest,
        source_dir,
        parsed_bands,
        parser_module="rsrf.parsers.usgs_json",
        parser_function="parse_usgs_json_directory",
    )


def _extract_usgs_curve_arrays(payload: list[object], filename: str) -> tuple[list[float], list[float]]:
    key_names: list[str] | None = None
    series_by_key: dict[str, list[float]] = {}
    for index, row in enumerate(payload, start=1):
        if not isinstance(row, dict) or len(row) < 2:
            raise ValueError(f"unexpected row structure in {filename} at index {index}")
        row_keys = list(row.keys())
        if key_names is None:
            key_names = row_keys
            series_by_key = {key: [] for key in key_names}
        elif set(row_keys) != set(key_names):
            raise ValueError(f"inconsistent USGS column keys in {filename} at index {index}")
        for key in key_names:
            series_by_key[key].append(_coerce_float(row[key], filename))

    if not key_names or len(key_names) != 2:
        raise ValueError(f"unexpected USGS column layout in {filename}")

    wavelength_key, response_key = _classify_usgs_curve_columns(series_by_key)
    wavelength_nm = [_scale_wavelength_nm(value) for value in series_by_key[wavelength_key]]
    response = series_by_key[response_key]
    return wavelength_nm, response


def _classify_usgs_curve_columns(series_by_key: dict[str, list[float]]) -> tuple[str, str]:
    keys = list(series_by_key)
    if len(keys) != 2:
        raise ValueError("USGS curve classification requires exactly two columns")

    spaced_keys = [key for key in keys if " " in key]
    if len(spaced_keys) == 1:
        wavelength_key = spaced_keys[0]
        response_key = keys[0] if keys[1] == wavelength_key else keys[1]
        return wavelength_key, response_key

    ranked = sorted(
        keys,
        key=lambda key: _series_wavelength_score(series_by_key[key]),
        reverse=True,
    )
    return ranked[0], ranked[1]


def _series_wavelength_score(values: list[float]) -> tuple[float, float, float]:
    if len(values) < 2:
        return (1.0, 0.0, 0.0)

    deltas = [right - left for left, right in zip(values, values[1:])]
    negative_steps = sum(1 for delta in deltas if delta < 0.0)
    total_variation = sum(abs(delta) for delta in deltas)
    monotonic_ratio = (
        1.0 if total_variation == 0.0 else abs(values[-1] - values[0]) / total_variation
    )
    span = abs(values[-1] - values[0])
    return (-negative_steps, monotonic_ratio, span)


def _scale_wavelength_nm(value: float) -> float:
    return value * 1000.0 if value < 100.0 else value


def _parse_usgs_band_identity(filename_stem: str, *, sensor_unit_id: str) -> tuple[str, int, str]:
    landsat_match = _LANDSAT_RE.match(filename_stem)
    if landsat_match:
        band_token = landsat_match.group("band")
        band_id, band_order = _normalize_landsat_band(band_token)
        return band_id, band_order, band_id

    aster_match = _ASTER_RE.match(filename_stem)
    if aster_match:
        band_token = aster_match.group("band")
        band_id, band_order = _normalize_aster_band(band_token)
        return band_id, band_order, band_id

    if filename_stem.startswith("TerraMODIS"):
        band_token = filename_stem.replace("TerraMODIS", "", 1).replace("thermal", "")
        band_number = int(band_token)
        return f"B{band_number}", band_number, f"B{band_number}"

    raise ValueError(
        f"unable to infer USGS band identity from {filename_stem!r} for sensor {sensor_unit_id}"
    )


def _normalize_landsat_band(token: str) -> tuple[str, int]:
    if token.endswith("pan"):
        band_number = int(token[:-3])
        return f"B{band_number}", band_number
    if token.startswith("thermal"):
        band_number = int(token.replace("thermal", "", 1))
        return f"B{band_number}", band_number
    band_number = int(token)
    return f"B{band_number}", band_number


def _normalize_aster_band(token: str) -> tuple[str, int]:
    token = token.upper()
    if token.startswith("THERMAL"):
        token = token.replace("THERMAL", "", 1)
    if token == "3N":
        return "B3N", 3
    if token == "3B":
        return "B3B", 4
    band_number = int(token)
    return f"B{band_number}", band_number if band_number < 3 else band_number + 1


def _coerce_float(value: object, filename: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"unable to parse numeric value in {filename}: {value!r}") from exc
