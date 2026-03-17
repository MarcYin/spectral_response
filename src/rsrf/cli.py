"""Command-line interface for the repository bootstrap."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

from .api import get_metadata, list_bands, list_sensors, load_response_definition
from .convolve import response_area
from .models import BandSpec, ManifestSummary, ManifestValidationError, SampledCurve
from .planning import list_planned_sensors, register_planned_sensor_catalog
from .qa import validate_sensor, write_validation_artifacts
from .registry import build_repo_layout, manifest_registry_rows, register_manifest
from .validate import parse_manifest_file


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI argument parser."""

    parser = argparse.ArgumentParser(
        prog="rsrf",
        description="Bootstrap tools for the spectral response function repository.",
    )
    subparsers = parser.add_subparsers(dest="command")

    show_layout = subparsers.add_parser("show-layout", help="print the repository layout")
    show_layout.add_argument(
        "--root",
        type=Path,
        default=None,
        help="repository root; defaults to the discovered current repository",
    )

    list_sensors_cmd = subparsers.add_parser(
        "list-sensors",
        help="list registered sensor representations with canonical artifacts",
    )
    list_sensors_cmd.add_argument(
        "--root",
        type=Path,
        default=None,
        help="repository root; defaults to the discovered current repository",
    )

    list_planned_cmd = subparsers.add_parser(
        "list-planned-sensors",
        help="list registry-first planned sensor representations from the planning catalog",
    )
    list_planned_cmd.add_argument(
        "--root",
        type=Path,
        default=None,
        help="repository root; defaults to the discovered current repository",
    )
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
    list_bands_cmd.add_argument(
        "--variant",
        dest="representation_variant",
        default=None,
        help="representation variant; required only when multiple variants exist",
    )
    list_bands_cmd.add_argument(
        "--root",
        type=Path,
        default=None,
        help="repository root; defaults to the discovered current repository",
    )

    show_metadata_cmd = subparsers.add_parser(
        "show-metadata",
        help="print canonical metadata for a sensor representation",
    )
    show_metadata_cmd.add_argument("sensor_unit_id")
    show_metadata_cmd.add_argument(
        "--variant",
        dest="representation_variant",
        default=None,
        help="representation variant; required only when multiple variants exist",
    )
    show_metadata_cmd.add_argument(
        "--root",
        type=Path,
        default=None,
        help="repository root; defaults to the discovered current repository",
    )

    show_response_cmd = subparsers.add_parser(
        "show-response",
        help="print a compact band-level response summary",
    )
    show_response_cmd.add_argument("sensor_unit_id")
    show_response_cmd.add_argument("band_id")
    show_response_cmd.add_argument(
        "--variant",
        dest="representation_variant",
        default=None,
        help="representation variant; required only when multiple variants exist",
    )
    show_response_cmd.add_argument(
        "--root",
        type=Path,
        default=None,
        help="repository root; defaults to the discovered current repository",
    )

    validate_sensor_cmd = subparsers.add_parser(
        "validate-sensor",
        help="validate a sensor representation and print the QA report",
    )
    validate_sensor_cmd.add_argument("sensor_unit_id")
    validate_sensor_cmd.add_argument(
        "--variant",
        dest="representation_variant",
        default=None,
        help="representation variant; required only when multiple variants exist",
    )
    validate_sensor_cmd.add_argument(
        "--root",
        type=Path,
        default=None,
        help="repository root; defaults to the discovered current repository",
    )

    export_validation_cmd = subparsers.add_parser(
        "export-validation",
        help="write a validation_report.json and overview.png for a sensor representation",
    )
    export_validation_cmd.add_argument("sensor_unit_id")
    export_validation_cmd.add_argument(
        "--variant",
        dest="representation_variant",
        default=None,
        help="representation variant; required only when multiple variants exist",
    )
    export_validation_cmd.add_argument(
        "--root",
        type=Path,
        default=None,
        help="repository root; defaults to the discovered current repository",
    )
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

    show_registry_rows = subparsers.add_parser(
        "show-registry-rows",
        help="print the registry rows derived from a manifest",
    )
    show_registry_rows.add_argument("manifest_path", type=Path)

    register_manifest_cmd = subparsers.add_parser(
        "register-manifest",
        help="upsert manifest-derived rows into data/registry parquet tables",
    )
    register_manifest_cmd.add_argument("manifest_path", type=Path)
    register_manifest_cmd.add_argument(
        "--root",
        type=Path,
        default=None,
        help="repository root; defaults to the discovered current repository",
    )

    register_planned_cmd = subparsers.add_parser(
        "register-planned-sensors",
        help="upsert planned sensor rows from the planning catalog into sensors.parquet",
    )
    register_planned_cmd.add_argument(
        "--root",
        type=Path,
        default=None,
        help="repository root; defaults to the discovered current repository",
    )
    register_planned_cmd.add_argument(
        "--catalog-path",
        type=Path,
        default=None,
        help="override the planning catalog path",
    )

    return parser


def _handle_show_layout(root: Path | None) -> int:
    layout = build_repo_layout(root)
    entries = {
        "root": layout.root,
        "package_root": layout.package_root,
        "registry_root": layout.registry_root,
        "canonical_root": layout.canonical_root,
        "realized_root": layout.realized_root,
        "common_grid_root": layout.common_grid_root,
        "source_manifests_root": layout.source_manifests_root,
        "ingest_scripts_root": layout.ingest_scripts_root,
        "tests_root": layout.tests_root,
    }
    for label, path in entries.items():
        print(f"{label}: {path}")
    return 0


def _print_manifest_errors(manifest_path: Path, errors: Sequence[str]) -> int:
    print(f"Manifest validation failed for {manifest_path}:")
    for error in errors:
        print(f"- {error}")
    return 1


def _normalize_json_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _normalize_json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_normalize_json_value(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "item") and callable(value.item):
        return _normalize_json_value(value.item())
    if value is None:
        return None
    if isinstance(value, float) and value != value:
        return None
    return value


def _print_json(payload: Any) -> int:
    normalized = _normalize_json_value(payload)
    print(json.dumps(normalized, indent=2, sort_keys=True, allow_nan=False))
    return 0


def _exception_message(exc: Exception) -> str:
    if exc.args:
        return str(exc.args[0])
    return str(exc)


def _handle_list_sensors(root: Path | None) -> int:
    try:
        sensors = list_sensors(root=root)
    except (FileNotFoundError, KeyError, RuntimeError, ValueError) as exc:
        print(_exception_message(exc))
        return 1
    return _print_json(sensors)


def _handle_list_planned_sensors(root: Path | None, catalog_path: Path | None) -> int:
    try:
        sensors = list_planned_sensors(root=root, catalog_path=catalog_path)
    except (FileNotFoundError, KeyError, RuntimeError, ValueError) as exc:
        print(_exception_message(exc))
        return 1
    return _print_json(sensors)


def _handle_list_bands(
    sensor_unit_id: str,
    representation_variant: str | None,
    root: Path | None,
) -> int:
    try:
        bands = list_bands(
            sensor_unit_id,
            representation_variant,
            root=root,
        )
    except (FileNotFoundError, KeyError, RuntimeError, ValueError) as exc:
        print(_exception_message(exc))
        return 1
    return _print_json(bands)


def _handle_show_metadata(
    sensor_unit_id: str,
    representation_variant: str | None,
    root: Path | None,
) -> int:
    try:
        metadata = get_metadata(
            sensor_unit_id,
            representation_variant,
            root=root,
        )
    except (FileNotFoundError, KeyError, RuntimeError, ValueError) as exc:
        print(_exception_message(exc))
        return 1
    return _print_json(metadata)


def _summarize_response_definition(
    sensor_unit_id: str,
    representation_variant: str,
    response_definition: SampledCurve | BandSpec,
) -> dict[str, Any]:
    if isinstance(response_definition, SampledCurve):
        return {
            "content_kind": "sampled_curve",
            "sensor_unit_id": sensor_unit_id,
            "representation_variant": representation_variant,
            "band_id": response_definition.band_id,
            "source_variant": response_definition.source_variant,
            "sample_count": len(response_definition.wavelength_nm),
            "wavelength_min_nm": float(min(response_definition.wavelength_nm)),
            "wavelength_max_nm": float(max(response_definition.wavelength_nm)),
            "peak_response": float(max(response_definition.response)),
            "area": response_area(response_definition),
        }
    return {
        "content_kind": "band_spec",
        "sensor_unit_id": sensor_unit_id,
        "representation_variant": representation_variant,
        "band_id": response_definition.band_id,
        "band_index": response_definition.band_index,
        "band_name": response_definition.band_name,
        "band_status": response_definition.band_status,
        "center_wavelength_nm": response_definition.center_wavelength_nm,
        "fwhm_nm": response_definition.fwhm_nm,
        "published_shape_type": response_definition.published_shape_type,
        "shape_param_json": dict(response_definition.shape_param_json),
    }


def _handle_show_response(
    sensor_unit_id: str,
    band_id: str,
    representation_variant: str | None,
    root: Path | None,
) -> int:
    try:
        metadata = get_metadata(sensor_unit_id, representation_variant, root=root)
        resolved_variant = str(metadata["representation_variant"])
        response_definition = load_response_definition(
            sensor_unit_id,
            band_id,
            resolved_variant,
            root=root,
        )
    except (FileNotFoundError, KeyError, RuntimeError, ValueError) as exc:
        print(_exception_message(exc))
        return 1

    payload = _summarize_response_definition(
        sensor_unit_id,
        resolved_variant,
        response_definition,
    )
    return _print_json(payload)


def _handle_validate_sensor(
    sensor_unit_id: str,
    representation_variant: str | None,
    root: Path | None,
) -> int:
    try:
        report = validate_sensor(
            sensor_unit_id,
            representation_variant,
            root=root,
        )
    except (FileNotFoundError, KeyError, RuntimeError, ValueError, NotImplementedError) as exc:
        print(_exception_message(exc))
        return 1
    _print_json(report)
    return 0 if report.get("passed") else 1


def _handle_export_validation(
    sensor_unit_id: str,
    representation_variant: str | None,
    root: Path | None,
    output_dir: Path | None,
) -> int:
    try:
        written = write_validation_artifacts(
            sensor_unit_id,
            representation_variant,
            root=root,
            output_dir=output_dir,
        )
    except (FileNotFoundError, KeyError, RuntimeError, ValueError, NotImplementedError) as exc:
        print(_exception_message(exc))
        return 1
    for label, path in written.items():
        print(f"{label}: {path}")
    return 0


def _handle_validate_manifest(manifest_path: Path) -> int:
    try:
        manifest = parse_manifest_file(manifest_path)
    except ManifestValidationError as exc:
        return _print_manifest_errors(manifest_path, exc.errors)

    summary = ManifestSummary.from_manifest(manifest)
    print(
        "Manifest OK: "
        f"{summary.sensor_unit_id} "
        f"[{summary.representation_variant}] "
        f"{summary.content_kind} "
        f"(tier {summary.source_tier})"
    )
    return 0


def _handle_show_registry_rows(manifest_path: Path) -> int:
    try:
        manifest = parse_manifest_file(manifest_path)
    except ManifestValidationError as exc:
        return _print_manifest_errors(manifest_path, exc.errors)

    rows = manifest_registry_rows(manifest)
    for table_name, table_rows in rows.items():
        print(f"[{table_name}]")
        if not table_rows:
            print("[]")
            continue
        for row in table_rows:
            print(json.dumps(dict(row), sort_keys=True))
    return 0


def _handle_register_manifest(manifest_path: Path, root: Path | None) -> int:
    try:
        manifest = parse_manifest_file(manifest_path)
    except ManifestValidationError as exc:
        return _print_manifest_errors(manifest_path, exc.errors)

    try:
        written = register_manifest(root, manifest)
    except RuntimeError as exc:
        print(str(exc))
        return 1

    if not written:
        print("No registry rows were written.")
        return 0

    for table_name, path in written.items():
        print(f"{table_name}: {path}")
    return 0


def _handle_register_planned_sensors(root: Path | None, catalog_path: Path | None) -> int:
    try:
        written = register_planned_sensor_catalog(root=root, catalog_path=catalog_path)
    except (FileNotFoundError, KeyError, RuntimeError, ValueError) as exc:
        print(_exception_message(exc))
        return 1

    if written is None:
        print("No planned sensor rows were written.")
        return 0

    print(f"sensors: {written}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI."""

    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.command == "show-layout":
        return _handle_show_layout(args.root)
    if args.command == "list-sensors":
        return _handle_list_sensors(args.root)
    if args.command == "list-planned-sensors":
        return _handle_list_planned_sensors(args.root, args.catalog_path)
    if args.command == "list-bands":
        return _handle_list_bands(
            args.sensor_unit_id,
            args.representation_variant,
            args.root,
        )
    if args.command == "show-metadata":
        return _handle_show_metadata(
            args.sensor_unit_id,
            args.representation_variant,
            args.root,
        )
    if args.command == "show-response":
        return _handle_show_response(
            args.sensor_unit_id,
            args.band_id,
            args.representation_variant,
            args.root,
        )
    if args.command == "validate-sensor":
        return _handle_validate_sensor(
            args.sensor_unit_id,
            args.representation_variant,
            args.root,
        )
    if args.command == "export-validation":
        return _handle_export_validation(
            args.sensor_unit_id,
            args.representation_variant,
            args.root,
            args.output_dir,
        )
    if args.command == "validate-manifest":
        return _handle_validate_manifest(args.manifest_path)
    if args.command == "show-registry-rows":
        return _handle_show_registry_rows(args.manifest_path)
    if args.command == "register-manifest":
        return _handle_register_manifest(args.manifest_path, args.root)
    if args.command == "register-planned-sensors":
        return _handle_register_planned_sensors(args.root, args.catalog_path)

    parser.print_help()
    return 0
