"""Bootstrap entrypoint for metadata-only band-spec ingest."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rsrf.ingest import write_band_spec_artifacts
from rsrf.models import ManifestSummary, ManifestValidationError
from rsrf.parsers.band_spec_table import parse_band_spec_table
from rsrf.validate import parse_manifest_file


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bootstrap band-spec ingest.")
    parser.add_argument(
        "manifest_path",
        nargs="?",
        type=Path,
        default=ROOT / "rsrf_source_manifest_hyperspectral_band_spec_example.json",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="parse the band-spec table and print a summary without writing outputs",
    )
    parser.add_argument(
        "--table-path",
        type=Path,
        default=None,
        help="override the band-spec table path instead of using manifest.raw_local_path",
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

    table_path = args.table_path or ROOT / manifest.raw_local_path
    try:
        artifacts = parse_band_spec_table(table_path, manifest)
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc))
        return 1

    summary = ManifestSummary.from_manifest(manifest)
    print(f"Validated manifest: {summary.source_id}")
    print(f"Band-spec table: {table_path}")
    print(f"Band-spec rows: {len(artifacts.band_spec_rows)}")
    print(f"Band rows: {len(artifacts.band_rows)}")
    print(f"Persist realized curves: {manifest.curve_realization.persist_realized_curves}")
    if args.dry_run:
        return 0

    try:
        written = write_band_spec_artifacts(ROOT, manifest, artifacts)
    except (RuntimeError, ValueError, NotImplementedError) as exc:
        print(str(exc))
        return 1

    for label, path in written.items():
        print(f"{label}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
