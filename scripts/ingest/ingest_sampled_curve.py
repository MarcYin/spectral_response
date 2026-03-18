"""Generic entrypoint for sampled-curve source ingests."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rsrf.ingest import write_sampled_curve_artifacts
from rsrf.models import ManifestSummary, ManifestValidationError
from rsrf.parsers import (
    parse_landsat_tirs_workbook,
    parse_multiband_curve_csv,
    parse_modis_rsr_workbook,
    parse_obpg_rsr_netcdf,
    parse_olci_mean_rsr_nc4,
    parse_probav_srf_workbook,
    parse_usgs_json_directory,
    parse_viirs_band_average_zip,
    parse_slstr_nwp_saf_tar,
)
from rsrf.validate import parse_manifest_file

PARSER_FUNCTIONS = {
    "parse_landsat_tirs_workbook": parse_landsat_tirs_workbook,
    "parse_multiband_curve_csv": parse_multiband_curve_csv,
    "parse_modis_rsr_workbook": parse_modis_rsr_workbook,
    "parse_obpg_rsr_netcdf": parse_obpg_rsr_netcdf,
    "parse_olci_mean_rsr_nc4": parse_olci_mean_rsr_nc4,
    "parse_probav_srf_workbook": parse_probav_srf_workbook,
    "parse_slstr_nwp_saf_tar": parse_slstr_nwp_saf_tar,
    "parse_usgs_json_directory": parse_usgs_json_directory,
    "parse_viirs_band_average_zip": parse_viirs_band_average_zip,
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bootstrap sampled-curve ingest.")
    parser.add_argument("manifest_path", type=Path)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="parse the source artifact and print a summary without writing outputs",
    )
    parser.add_argument(
        "--source-path",
        type=Path,
        default=None,
        help="override the source path instead of using manifest.raw_local_path",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        manifest = parse_manifest_file(args.manifest_path, root=ROOT)
    except ManifestValidationError as exc:
        for error in exc.errors:
            print(error)
        return 1

    parser_function = PARSER_FUNCTIONS.get(manifest.parser.entrypoint)
    if parser_function is None:
        print(f"unsupported sampled-curve parser entrypoint: {manifest.parser.entrypoint}")
        return 1

    source_path = args.source_path or ROOT / manifest.raw_local_path
    try:
        artifacts = parser_function(source_path, manifest)
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc))
        return 1

    summary = ManifestSummary.from_manifest(manifest)
    print(f"Validated manifest: {summary.source_id}")
    print(f"Source artifact: {source_path}")
    print(f"Curve rows: {len(artifacts.curve_rows)}")
    print(f"Band rows: {len(artifacts.band_rows)}")
    if args.dry_run:
        return 0

    try:
        written = write_sampled_curve_artifacts(ROOT, manifest, artifacts)
    except RuntimeError as exc:
        print(str(exc))
        return 1

    for label, path in written.items():
        print(f"{label}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
