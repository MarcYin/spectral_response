from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import xarray as xr

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rsrf.io import read_json
from rsrf.parsers.olci import parse_olci_mean_rsr_nc4
from rsrf.validate import parse_manifest_dict


def _manifest_for(sensor_unit_id: str) -> dict:
    payload = read_json(ROOT / "rsrf_source_manifest_sentinel2c_v2.json")
    payload["source_id"] = f"{sensor_unit_id}_olci_test"
    payload["sensor_unit_id"] = sensor_unit_id
    payload["title"] = f"{sensor_unit_id} OLCI test source"
    payload["url"] = "https://sentiwiki.copernicus.eu/web/s3-documents"
    payload["doc_version"] = "test"
    payload["raw_local_path"] = "sources/raw/test.nc4"
    payload["file_sha256"] = "test"
    payload["parser"]["script"] = "scripts/ingest/ingest_sampled_curve.py"
    payload["parser"]["entrypoint"] = "parse_olci_mean_rsr_nc4"
    payload["validation"]["plot_overlay_required"] = False
    payload["validation"]["expected_band_count"] = 2
    return payload


class OlciParserTests(unittest.TestCase):
    def test_parser_extracts_mean_rsr_dataset(self) -> None:
        manifest = parse_manifest_dict(_manifest_for("sentinel-3a_olci"))
        with tempfile.TemporaryDirectory() as tmpdir:
            dataset_path = Path(tmpdir) / "fixture.nc4"
            dataset = xr.Dataset(
                data_vars={
                    "mean_spectral_response_function": (
                        ("band_number", "wavelength"),
                        np.asarray([[0.0, 1.0, 0.0], [0.0, 0.5, 0.0]], dtype=np.float32),
                    ),
                    "mean_spectral_response_function_wavelength": (
                        ("band_number", "wavelength"),
                        np.asarray([[400.0, 401.0, 402.0], [500.0, 501.0, 502.0]], dtype=np.float32),
                    ),
                    "bandwidth_fwhm": (("band_number",), np.asarray([1.0, 2.0], dtype=np.float32)),
                    "srf_centre_wavelength": (("band_number",), np.asarray([401.0, 501.0], dtype=np.float32)),
                }
            )
            dataset.to_netcdf(dataset_path, engine="netcdf4")
            artifacts = parse_olci_mean_rsr_nc4(dataset_path, manifest)

        self.assertEqual(len(artifacts.band_rows), 2)
        self.assertEqual(artifacts.band_rows[0]["band_id"], "B01")
        self.assertEqual(artifacts.curve_rows[0]["wavelength_nm"], 400.0)


if __name__ == "__main__":
    unittest.main()
