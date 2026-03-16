"""Bootstrap entrypoint for Sentinel-2 SRF ingest."""

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
from rsrf.parsers.sentinel2 import parse_s2_srf_xlsx
from rsrf.validate import parse_manifest_file


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bootstrap Sentinel-2 SRF ingest.")
    parser.add_argument(
        "manifest_path",
        nargs="?",
        type=Path,
        default=ROOT / "rsrf_source_manifest_sentinel2c_v2.json",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="parse the workbook and print a summary without writing outputs",
    )
    parser.add_argument(
        "--workbook-path",
        type=Path,
        default=None,
        help="override the workbook path instead of using manifest.raw_local_path",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        manifest = parse_manifest_file(args.manifest_path)
    except ManifestValidationError as exc:
        for error in exc.errors:
            print(error)
        return 1

    workbook_path = args.workbook_path or ROOT / manifest.raw_local_path
    try:
        artifacts = parse_s2_srf_xlsx(workbook_path, manifest)
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc))
        return 1

    summary = ManifestSummary.from_manifest(manifest)
    print(f"Validated manifest: {summary.source_id}")
    print(f"Workbook: {workbook_path}")
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
