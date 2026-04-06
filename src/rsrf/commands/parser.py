"""Argument parser builder for the ``rsrf`` CLI."""

from __future__ import annotations

import argparse
from pathlib import Path

from .. import __version__


def _add_root_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="override the default RSRF root (local repo, RSRF_ROOT, or cached GitHub release snapshot)",
    )


def _add_variant_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--variant",
        dest="representation_variant",
        default=None,
        help="representation variant; required only when multiple variants exist",
    )


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI argument parser."""

    parser = argparse.ArgumentParser(
        prog="rsrf",
        description="Canonical spectral response function repository toolkit.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    subparsers = parser.add_subparsers(dest="command")

    show_layout = subparsers.add_parser("show-layout", help="print the repository layout")
    _add_root_argument(show_layout)

    list_sensors_cmd = subparsers.add_parser(
        "list-sensors",
        help="list registered sensor representations with canonical artifacts",
    )
    _add_root_argument(list_sensors_cmd)

    list_planned_cmd = subparsers.add_parser(
        "list-planned-sensors",
        help="list registry-first planned sensor representations from the planning catalog",
    )
    _add_root_argument(list_planned_cmd)
    list_planned_cmd.add_argument(
        "--catalog-path",
        type=Path,
        default=None,
        help="override the planning catalog path",
    )

    list_bands_cmd = subparsers.add_parser(
        "list-bands",
        help="list canonical band rows for a sensor representation",
    )
    list_bands_cmd.add_argument("sensor_unit_id")
    _add_variant_argument(list_bands_cmd)
    _add_root_argument(list_bands_cmd)

    show_metadata_cmd = subparsers.add_parser(
        "show-metadata",
        help="print canonical metadata for a sensor representation",
    )
    show_metadata_cmd.add_argument("sensor_unit_id")
    _add_variant_argument(show_metadata_cmd)
    _add_root_argument(show_metadata_cmd)

    show_response_cmd = subparsers.add_parser(
        "show-response",
        help="print a compact band-level response summary",
    )
    show_response_cmd.add_argument("sensor_unit_id")
    show_response_cmd.add_argument("band_id")
    _add_variant_argument(show_response_cmd)
    _add_root_argument(show_response_cmd)

    validate_sensor_cmd = subparsers.add_parser(
        "validate-sensor",
        help="validate a sensor representation and print the QA report",
    )
    validate_sensor_cmd.add_argument("sensor_unit_id")
    _add_variant_argument(validate_sensor_cmd)
    _add_root_argument(validate_sensor_cmd)

    export_validation_cmd = subparsers.add_parser(
        "export-validation",
        help="write a validation_report.json and overview.png for a sensor representation",
    )
    export_validation_cmd.add_argument("sensor_unit_id")
    _add_variant_argument(export_validation_cmd)
    _add_root_argument(export_validation_cmd)
    export_validation_cmd.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="directory for validation artifacts; defaults to docs/sensor-notes/<sensor>/<variant>",
    )

    validate_manifest = subparsers.add_parser(
        "validate-manifest",
        help="validate a source manifest JSON file",
    )
    validate_manifest.add_argument("manifest_path", type=Path)
    _add_root_argument(validate_manifest)

    show_registry_rows = subparsers.add_parser(
        "show-registry-rows",
        help="print the registry rows derived from a manifest",
    )
    show_registry_rows.add_argument("manifest_path", type=Path)
    _add_root_argument(show_registry_rows)

    register_manifest_cmd = subparsers.add_parser(
        "register-manifest",
        help="upsert manifest-derived rows into data/registry parquet tables",
    )
    register_manifest_cmd.add_argument("manifest_path", type=Path)
    _add_root_argument(register_manifest_cmd)

    register_planned_cmd = subparsers.add_parser(
        "register-planned-sensors",
        help="upsert planned sensor rows from the planning catalog into sensors.parquet",
    )
    _add_root_argument(register_planned_cmd)
    register_planned_cmd.add_argument(
        "--catalog-path",
        type=Path,
        default=None,
        help="override the planning catalog path",
    )

    return parser
