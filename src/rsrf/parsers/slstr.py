"""Parser for Sentinel-3 SLSTR spectral response archives from EUMETSAT NWP SAF."""

from __future__ import annotations

import re
import tarfile
from pathlib import Path

from ..models import SourceManifest
from .common import ParsedBandCurve, build_sampled_curve_artifacts

_SLSTR_MEMBER_RE = re.compile(r"_ch(?P<channel>\d{2})\.txt$", re.IGNORECASE)
_SLSTR_HEADER_RE = re.compile(r"SLSTR\s+(?P<band>S\d+)\b", re.IGNORECASE)
_SLSTR_BAND_ORDER = {
    "S1": 1,
    "S2": 2,
    "S3": 3,
    "S4": 4,
    "S5": 5,
    "S6": 6,
    "S7": 7,
    "S8": 8,
    "S9": 9,
    "F1": 10,
    "F2": 11,
}
_DUPLICATED_FIRE_BANDS = {
    "F1": "S7",
    "F2": "S8",
}


def parse_slstr_nwp_saf_tar(archive_path: Path, manifest: SourceManifest):
    """Parse official Sentinel-3 SLSTR spectral response tar archives."""

    if not archive_path.exists():
        raise FileNotFoundError(f"SLSTR SRF archive not found: {archive_path}")

    parsed_bands: list[ParsedBandCurve] = []
    with tarfile.open(archive_path, "r:gz") as archive:
        members = _select_curve_members(archive)
        if not members:
            raise ValueError(f"no SLSTR SRF text members found in archive: {archive_path}")

        for member in members:
            extracted = archive.extractfile(member)
            if extracted is None:
                raise ValueError(f"unable to read member from SLSTR archive: {member.name}")
            text = extracted.read().decode("utf-8", errors="replace")
            parsed_bands.append(_parse_slstr_member_text(text, member.name))

    band_by_id = {band.band_id: band for band in parsed_bands}
    for duplicate_band_id, source_band_id in _DUPLICATED_FIRE_BANDS.items():
        source_band = band_by_id.get(source_band_id)
        if source_band is None:
            raise ValueError(f"missing required SLSTR source band for duplication: {source_band_id}")
        parsed_bands.append(
            ParsedBandCurve(
                band_id=duplicate_band_id,
                band_index=_SLSTR_BAND_ORDER[duplicate_band_id],
                band_name=duplicate_band_id,
                wavelength_nm=list(source_band.wavelength_nm),
                response=list(source_band.response),
                band_status="source_equivalent_curve",
            )
        )

    parsed_bands.sort(key=lambda band: (_SLSTR_BAND_ORDER[band.band_id], band.band_id))
    return build_sampled_curve_artifacts(
        manifest,
        archive_path,
        parsed_bands,
        parser_module="rsrf.parsers.slstr",
        parser_function="parse_slstr_nwp_saf_tar",
        extra_metadata={
            "slstr_srf": {
                "source_archive_member_count": len(parsed_bands) - len(_DUPLICATED_FIRE_BANDS),
                "source_axis": "wavenumber_cm-1",
                "derived_band_duplicates": dict(_DUPLICATED_FIRE_BANDS),
            }
        },
    )


def _select_curve_members(archive: tarfile.TarFile) -> list[tarfile.TarInfo]:
    selected: list[tarfile.TarInfo] = []
    for member in archive.getmembers():
        if not member.isfile():
            continue
        match = _SLSTR_MEMBER_RE.search(member.name)
        if match is None:
            continue
        selected.append(member)
    selected.sort(key=lambda member: int(_SLSTR_MEMBER_RE.search(member.name).group("channel")))
    return selected


def _parse_slstr_member_text(text: str, member_name: str) -> ParsedBandCurve:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) < 5:
        raise ValueError(f"unexpected SLSTR SRF member format in {member_name}")

    header_match = _SLSTR_HEADER_RE.search(lines[0])
    if header_match is None:
        raise ValueError(f"unable to infer SLSTR band id from header in {member_name}")
    band_id = header_match.group("band").upper()
    if band_id not in _SLSTR_BAND_ORDER:
        raise ValueError(f"unsupported SLSTR band id {band_id!r} in {member_name}")

    try:
        expected_point_count = int(lines[2])
    except ValueError as exc:
        raise ValueError(f"invalid SLSTR point count in {member_name}: {lines[2]!r}") from exc

    wavelength_nm: list[float] = []
    response: list[float] = []
    for line in lines[4:]:
        parts = line.split()
        if len(parts) != 2:
            continue
        wavenumber_cm_inverse = float(parts[0])
        response_value = float(parts[1])
        wavelength_nm.append(1.0e7 / wavenumber_cm_inverse)
        response.append(response_value)

    if not wavelength_nm:
        raise ValueError(f"no numeric SLSTR samples found in {member_name}")
    if len(wavelength_nm) != expected_point_count:
        raise ValueError(
            f"SLSTR SRF point-count mismatch in {member_name}: expected {expected_point_count}, got {len(wavelength_nm)}"
        )

    return ParsedBandCurve(
        band_id=band_id,
        band_index=_SLSTR_BAND_ORDER[band_id],
        band_name=band_id,
        wavelength_nm=wavelength_nm,
        response=response,
    )
