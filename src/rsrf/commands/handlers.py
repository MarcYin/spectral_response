"""Command handlers for the ``rsrf`` CLI."""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path

from ..api import get_metadata, list_bands, list_sensors, load_response_definition
from ..models import ManifestSummary, ManifestValidationError
from ..planning import list_planned_sensors, register_planned_sensor_catalog
from ..qa import validate_sensor, write_validation_artifacts
from ..registry import build_repo_layout, manifest_registry_rows, register_manifest
from ..validate import parse_manifest_file
from .render import (
    exception_message,
    print_json,
    print_manifest_errors,
    summarize_response_definition,
)


def handle_show_layout(args: Namespace) -> int:
    layout = build_repo_layout(args.root)
    entries = {
        "root": layout.root,
        "package_root": layout.package_root,
        "registry_root": layout.registry_root,
        "canonical_root": layout.canonical_root,
        "realized_root": layout.realized_root,
        "common_grid_root": layout.common_grid_root,
        "source_manifests_root": layout.source_manifests_root,
        "official_source_manifests_root": layout.official_source_manifests_root,
        "planning_source_manifests_root": layout.planning_source_manifests_root,
        "template_source_manifests_root": layout.template_source_manifests_root,
        "ingest_scripts_root": layout.ingest_scripts_root,
        "tests_root": layout.tests_root,
    }
    for label, path in entries.items():
        print(f"{label}: {path}")
    return 0


def handle_list_sensors(args: Namespace) -> int:
    try:
        sensors = list_sensors(root=args.root)
    except (FileNotFoundError, KeyError, RuntimeError, ValueError) as exc:
        print(exception_message(exc))
        return 1
    return print_json(sensors)


def handle_list_planned_sensors(args: Namespace) -> int:
    try:
        sensors = list_planned_sensors(root=args.root, catalog_path=args.catalog_path)
    except (FileNotFoundError, KeyError, RuntimeError, ValueError) as exc:
        print(exception_message(exc))
        return 1
    return print_json(sensors)


def handle_list_bands(args: Namespace) -> int:
    try:
        bands = list_bands(
            args.sensor_unit_id,
            args.representation_variant,
            root=args.root,
        )
    except (FileNotFoundError, KeyError, RuntimeError, ValueError) as exc:
        print(exception_message(exc))
        return 1
    return print_json(bands)


def handle_show_metadata(args: Namespace) -> int:
    try:
        metadata = get_metadata(
            args.sensor_unit_id,
            args.representation_variant,
            root=args.root,
        )
    except (FileNotFoundError, KeyError, RuntimeError, ValueError) as exc:
        print(exception_message(exc))
        return 1
    return print_json(metadata)


def handle_show_response(args: Namespace) -> int:
    try:
        metadata = get_metadata(
            args.sensor_unit_id,
            args.representation_variant,
            root=args.root,
        )
        resolved_variant = str(metadata["representation_variant"])
        response_definition = load_response_definition(
            args.sensor_unit_id,
            args.band_id,
            resolved_variant,
            root=args.root,
        )
    except (FileNotFoundError, KeyError, RuntimeError, ValueError) as exc:
        print(exception_message(exc))
        return 1

    payload = summarize_response_definition(
        args.sensor_unit_id,
        resolved_variant,
        response_definition,
    )
    return print_json(payload)


def handle_validate_sensor(args: Namespace) -> int:
    try:
        report = validate_sensor(
            args.sensor_unit_id,
            args.representation_variant,
            root=args.root,
        )
    except (FileNotFoundError, KeyError, RuntimeError, ValueError, NotImplementedError) as exc:
        print(exception_message(exc))
        return 1
    print_json(report)
    return 0 if report.get("passed") else 1


def handle_export_validation(args: Namespace) -> int:
    try:
        written = write_validation_artifacts(
            args.sensor_unit_id,
            args.representation_variant,
            root=args.root,
            output_dir=args.output_dir,
        )
    except (FileNotFoundError, KeyError, RuntimeError, ValueError, NotImplementedError) as exc:
        print(exception_message(exc))
        return 1
    for label, path in written.items():
        print(f"{label}: {path}")
    return 0


def handle_validate_manifest(args: Namespace) -> int:
    manifest_path = Path(args.manifest_path)
    try:
        manifest = parse_manifest_file(manifest_path, root=args.root)
    except ManifestValidationError as exc:
        return print_manifest_errors(manifest_path, exc.errors)

    summary = ManifestSummary.from_manifest(manifest)
    print(
        "Manifest OK: "
        f"{summary.sensor_unit_id} "
        f"[{summary.representation_variant}] "
        f"{summary.content_kind} "
        f"(tier {summary.source_tier})"
    )
    return 0


def handle_show_registry_rows(args: Namespace) -> int:
    manifest_path = Path(args.manifest_path)
    try:
        manifest = parse_manifest_file(manifest_path, root=args.root)
    except ManifestValidationError as exc:
        return print_manifest_errors(manifest_path, exc.errors)

    rows = manifest_registry_rows(manifest)
    for table_name, table_rows in rows.items():
        print(f"[{table_name}]")
        if not table_rows:
            print("[]")
            continue
        for row in table_rows:
            print_json(dict(row))
    return 0


def handle_register_manifest(args: Namespace) -> int:
    manifest_path = Path(args.manifest_path)
    try:
        manifest = parse_manifest_file(manifest_path, root=args.root)
    except ManifestValidationError as exc:
        return print_manifest_errors(manifest_path, exc.errors)

    try:
        written = register_manifest(args.root, manifest)
    except RuntimeError as exc:
        print(str(exc))
        return 1

    if not written:
        print("No registry rows were written.")
        return 0

    for table_name, path in written.items():
        print(f"{table_name}: {path}")
    return 0


def handle_register_planned_sensors(args: Namespace) -> int:
    try:
        written = register_planned_sensor_catalog(root=args.root, catalog_path=args.catalog_path)
    except (FileNotFoundError, KeyError, RuntimeError, ValueError) as exc:
        print(exception_message(exc))
        return 1

    if written is None:
        print("No planned sensor rows were written.")
        return 0

    print(f"sensors: {written}")
    return 0
