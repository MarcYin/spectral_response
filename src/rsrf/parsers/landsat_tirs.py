"""Parser for Landsat 8/9 TIRS official workbook exports."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ..models import SourceManifest
from .common import ParsedBandCurve, build_sampled_curve_artifacts


def parse_landsat_tirs_workbook(workbook_path: Path, manifest: SourceManifest):
    """Parse the Landsat 8/9 TIRS band-average workbook."""

    if not workbook_path.exists():
        raise FileNotFoundError(f"workbook not found: {workbook_path}")

    workbook = pd.ExcelFile(workbook_path)
    try:
        bands: list[ParsedBandCurve]
        if "TIRS BA RSR" in workbook.sheet_names:
            bands = _parse_landsat8_tirs(workbook)
        else:
            bands = _parse_landsat9_tirs(workbook)
    finally:
        workbook.close()

    return build_sampled_curve_artifacts(
        manifest,
        workbook_path,
        bands,
        parser_module="rsrf.parsers.landsat_tirs",
        parser_function="parse_landsat_tirs_workbook",
    )


def _parse_landsat8_tirs(workbook: pd.ExcelFile) -> list[ParsedBandCurve]:
    frame = workbook.parse("TIRS BA RSR")
    frame = frame.rename(columns=lambda value: str(value).strip())
    wavelength_column = _find_column(frame.columns, "wavelength [um]")
    band_10_column = _find_column(frame.columns, "TIRS1 10.8um band average")
    band_11_column = _find_column(frame.columns, "TIRS2 12.0um band average")
    valid = frame[[wavelength_column, band_10_column, band_11_column]].dropna()
    wavelength_nm = (valid[wavelength_column].astype(float) * 1000.0).tolist()
    return [
        ParsedBandCurve(
            band_id="B10",
            band_index=10,
            band_name="B10",
            wavelength_nm=wavelength_nm,
            response=valid[band_10_column].astype(float).tolist(),
        ),
        ParsedBandCurve(
            band_id="B11",
            band_index=11,
            band_name="B11",
            wavelength_nm=wavelength_nm,
            response=valid[band_11_column].astype(float).tolist(),
        ),
    ]


def _parse_landsat9_tirs(workbook: pd.ExcelFile) -> list[ParsedBandCurve]:
    bands: list[ParsedBandCurve] = []
    for band_number in (10, 11):
        sheet_name = f"TIRS Band {band_number} BA RSR"
        if sheet_name not in workbook.sheet_names:
            raise ValueError(f"required sheet not found in Landsat TIRS workbook: {sheet_name}")
        frame = workbook.parse(sheet_name)
        frame = frame.rename(columns=lambda value: str(value).strip())
        wavelength_column = _find_column(frame.columns, "wavelength [um]")
        response_column = next(
            (str(column) for column in frame.columns if "RSR" in str(column)),
            None,
        )
        if response_column is None:
            raise ValueError(f"RSR column not found in sheet: {sheet_name}")
        valid = frame[[wavelength_column, response_column]].dropna()
        bands.append(
            ParsedBandCurve(
                band_id=f"B{band_number}",
                band_index=band_number,
                band_name=f"B{band_number}",
                wavelength_nm=(valid[wavelength_column].astype(float) * 1000.0).tolist(),
                response=valid[response_column].astype(float).tolist(),
            )
        )
    return bands


def _find_column(columns, needle: str) -> str:
    normalized = needle.lower()
    for column in columns:
        if str(column).strip().lower() == normalized:
            return str(column)
    raise ValueError(f"required column not found: {needle}")
