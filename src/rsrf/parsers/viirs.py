"""Parser for official VIIRS band-average RSR zip bundles."""

from __future__ import annotations

import re
from pathlib import Path
from zipfile import ZipFile

from ..models import SourceManifest
from .common import ParsedBandCurve, build_sampled_curve_artifacts

_BAND_TOKEN_RE = re.compile(r"_(?P<band>(?:M\d{1,2}(?:A|B)?)|(?:I\d)|(?:DNB[A-Z]+))_")


def parse_viirs_band_average_zip(zip_path: Path, manifest: SourceManifest):
    """Parse official VIIRS band-average zip bundles."""

    if not zip_path.exists():
        raise FileNotFoundError(f"zip archive not found: {zip_path}")

    with ZipFile(zip_path) as archive:
        selected_members = _select_band_average_members(archive.namelist())
        if not selected_members:
            raise ValueError(f"no band-average VIIRS members found in archive: {zip_path}")

        parsed_bands: list[ParsedBandCurve] = []
        for member_name in selected_members:
            band_token = _extract_band_token(member_name)
            lines = archive.read(member_name).decode("utf-8", errors="replace").splitlines()
            wavelength_nm, response = _parse_viirs_lines(lines)
            parsed_bands.append(
                ParsedBandCurve(
                    band_id=band_token,
                    band_index=_band_order(band_token),
                    band_name=band_token,
                    wavelength_nm=wavelength_nm,
                    response=response,
                )
            )

    parsed_bands.sort(key=lambda band: (band.band_index or 0, band.band_id))
    return build_sampled_curve_artifacts(
        manifest,
        zip_path,
        parsed_bands,
        parser_module="rsrf.parsers.viirs",
        parser_function="parse_viirs_band_average_zip",
    )


def _select_band_average_members(member_names: list[str]) -> list[str]:
    candidates_by_band: dict[str, tuple[int, str]] = {}
    for member_name in member_names:
        normalized_name = member_name.replace("\\", "/")
        lower_name = normalized_name.lower()
        basename = normalized_name.rsplit("/", maxsplit=1)[-1]
        if basename.startswith("._") or basename == ".DS_Store":
            continue
        if not lower_name.endswith((".txt", ".dat")):
            continue
        if "detector" in lower_name:
            continue
        if (
            "_ba_" not in lower_name
            and "_ba." not in lower_name
            and "_ba_" not in normalized_name
            and "/j1_viirs_ba_rsr_" not in lower_name
            and "/j2_viirs_ba_rsr_" not in lower_name
        ):
            continue
        band_token = _extract_band_token(normalized_name)
        if band_token.startswith("DNB"):
            continue
        priority = _member_priority(normalized_name)
        previous = candidates_by_band.get(band_token)
        if previous is None or priority > previous[0]:
            candidates_by_band[band_token] = (priority, normalized_name)
    if "M16" in candidates_by_band and {"M16A", "M16B"} & set(candidates_by_band):
        candidates_by_band.pop("M16")
    return [
        item[1]
        for item in sorted(candidates_by_band.values(), key=lambda value: _band_order(_extract_band_token(value[1])))
    ]


def _member_priority(member_name: str) -> int:
    lower_name = member_name.lower()
    if "v2.1f" in lower_name:
        return 4
    if "v2f" in lower_name:
        return 3
    if "oct2011f" in lower_name:
        return 2
    if "v1" in lower_name:
        return 1
    return 0


def _extract_band_token(member_name: str) -> str:
    match = _BAND_TOKEN_RE.search(member_name)
    if match is None:
        raise ValueError(f"unable to extract VIIRS band token from {member_name!r}")
    return match.group("band")


def _parse_viirs_lines(lines: list[str]) -> tuple[list[float], list[float]]:
    wavelength_nm: list[float] = []
    response: list[float] = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("%"):
            continue
        parts = stripped.split()
        if len(parts) == 2:
            wavelength_value, response_value = parts
        elif len(parts) >= 3:
            wavelength_value, response_value = parts[-2], parts[-1]
        else:
            continue
        wavelength_nm.append(float(wavelength_value))
        response.append(float(response_value))
    if not wavelength_nm:
        raise ValueError("VIIRS file did not contain any numeric curve samples")
    return wavelength_nm, response


def _band_order(band_token: str) -> int:
    if band_token.startswith("M"):
        if band_token.endswith("A"):
            return int(band_token[1:-1]) * 10
        if band_token.endswith("B"):
            return int(band_token[1:-1]) * 10 + 1
        return int(band_token[1:]) * 10
    if band_token.startswith("I"):
        return 1000 + int(band_token[1:])
    raise ValueError(f"unsupported VIIRS band token: {band_token}")
