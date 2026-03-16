"""Parser for official Sentinel-3 OLCI mean RSR netCDF files."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import xarray as xr

from ..models import SourceManifest
from .common import ParsedBandCurve, build_sampled_curve_artifacts


def parse_olci_mean_rsr_nc4(netcdf_path: Path, manifest: SourceManifest):
    """Parse the official OLCI mean spectral-response netCDF file."""

    if not netcdf_path.exists():
        raise FileNotFoundError(f"netCDF file not found: {netcdf_path}")

    dataset = xr.open_dataset(netcdf_path, engine="netcdf4")
    try:
        response_array = dataset["mean_spectral_response_function"]
        wavelength_array = dataset["mean_spectral_response_function_wavelength"]
        band_count = int(response_array.sizes["band_number"])
        bands: list[ParsedBandCurve] = []
        for band_offset in range(band_count):
            wavelength_nm = np.asarray(
                wavelength_array.isel(band_number=band_offset).values,
                dtype=float,
            )
            response = np.asarray(
                response_array.isel(band_number=band_offset).values,
                dtype=float,
            )
            valid_mask = np.isfinite(wavelength_nm) & np.isfinite(response)
            bands.append(
                ParsedBandCurve(
                    band_id=f"B{band_offset + 1:02d}",
                    band_index=band_offset + 1,
                    band_name=f"B{band_offset + 1:02d}",
                    wavelength_nm=wavelength_nm[valid_mask].tolist(),
                    response=response[valid_mask].tolist(),
                )
            )
    finally:
        dataset.close()

    return build_sampled_curve_artifacts(
        manifest,
        netcdf_path,
        bands,
        parser_module="rsrf.parsers.olci",
        parser_function="parse_olci_mean_rsr_nc4",
    )
