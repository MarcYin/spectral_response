"""Parsers for official MODIS RSR workbooks."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from ..models import SourceManifest
from .common import ParsedBandCurve, build_sampled_curve_artifacts

_AQUA_BAND_SHEET_RE = re.compile(r"^band_(?P<band>\d+)$", re.IGNORECASE)
_TERRA_BAND_RE = re.compile(r"^Band\s+(?P<band>\d+)$", re.IGNORECASE)


def parse_modis_rsr_workbook(workbook_path: Path, manifest: SourceManifest):
    """Parse Terra or Aqua MODIS RSR workbooks."""

    if not workbook_path.exists():
        raise FileNotFoundError(f"workbook not found: {workbook_path}")

    workbook = pd.ExcelFile(workbook_path)
    try:
        if any(_AQUA_BAND_SHEET_RE.match(sheet_name) for sheet_name in workbook.sheet_names):
            bands = _parse_aqua_modis_workbook(workbook)
        else:
            bands = _parse_terra_modis_workbook(workbook)
    finally:
        workbook.close()

    return build_sampled_curve_artifacts(
        manifest,
        workbook_path,
        bands,
        parser_module="rsrf.parsers.modis",
        parser_function="parse_modis_rsr_workbook",
    )


def _parse_aqua_modis_workbook(workbook: pd.ExcelFile) -> list[ParsedBandCurve]:
    bands: list[ParsedBandCurve] = []
    for sheet_name in workbook.sheet_names:
        match = _AQUA_BAND_SHEET_RE.match(sheet_name)
        if not match:
            continue
        band_number = int(match.group("band"))
        frame = workbook.parse(sheet_name)
        frame = frame.rename(columns=lambda value: str(value).strip())
        wavelength_column = _find_column(frame.columns, "Wavelength")
        response_column = _find_column(frame.columns, "InbandPeakMethodRSR")
        valid_rows = frame[[wavelength_column, response_column]].dropna()
        bands.append(
            ParsedBandCurve(
                band_id=f"B{band_number}",
                band_index=band_number,
                band_name=f"B{band_number}",
                wavelength_nm=valid_rows[wavelength_column].astype(float).tolist(),
                response=valid_rows[response_column].astype(float).tolist(),
            )
        )
    if not bands:
        raise ValueError("Aqua MODIS workbook did not contain any band sheets")
    bands.sort(key=lambda band: band.band_index or 0)
    return bands


def _parse_terra_modis_workbook(workbook: pd.ExcelFile) -> list[ParsedBandCurve]:
    sheet_name = workbook.sheet_names[0]
    frame = workbook.parse(sheet_name, header=None)
    header_row = frame.iloc[0].tolist()
    units_row = frame.iloc[1].tolist()
    data_frame = frame.iloc[2:].reset_index(drop=True)

    bands: list[ParsedBandCurve] = []
    for column_index in range(0, len(header_row), 2):
        if column_index + 1 >= len(header_row):
            continue
        band_label = header_row[column_index]
        unit_label = units_row[column_index]
        response_label = units_row[column_index + 1]
        if not isinstance(band_label, str):
            continue
        band_match = _TERRA_BAND_RE.match(band_label.strip())
        if band_match is None:
            continue
        if str(unit_label).strip() != "Wvln(mm)" or str(response_label).strip() != "RSR":
            continue
        band_number = int(band_match.group("band"))
        valid_rows = data_frame.iloc[:, [column_index, column_index + 1]].dropna()
        wavelength_nm = (valid_rows.iloc[:, 0].astype(float) * 1000.0).tolist()
        response = valid_rows.iloc[:, 1].astype(float).tolist()
        bands.append(
            ParsedBandCurve(
                band_id=f"B{band_number}",
                band_index=band_number,
                band_name=f"B{band_number}",
                wavelength_nm=wavelength_nm,
                response=response,
            )
        )

    if not bands:
        raise ValueError("Terra MODIS workbook did not contain any band pairs")
    bands.sort(key=lambda band: band.band_index or 0)
    return bands


def _find_column(columns, needle: str) -> str:
    normalized = needle.lower()
    for column in columns:
        if str(column).strip().lower() == normalized:
            return str(column)
    raise ValueError(f"required column not found: {needle}")
