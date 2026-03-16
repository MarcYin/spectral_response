"""Command-line interface for the repository bootstrap."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .models import ManifestSummary, ManifestValidationError
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


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI."""

    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.command == "show-layout":
        return _handle_show_layout(args.root)
    if args.command == "validate-manifest":
        return _handle_validate_manifest(args.manifest_path)
    if args.command == "show-registry-rows":
        return _handle_show_registry_rows(args.manifest_path)
    if args.command == "register-manifest":
        return _handle_register_manifest(args.manifest_path, args.root)

    parser.print_help()
    return 0
