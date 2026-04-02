"""Application entrypoint for the ``rsrf`` CLI."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Callable

from .handlers import (
    handle_export_validation,
    handle_list_bands,
    handle_list_planned_sensors,
    handle_list_sensors,
    handle_register_manifest,
    handle_register_planned_sensors,
    handle_show_layout,
    handle_show_metadata,
    handle_show_registry_rows,
    handle_show_response,
    handle_validate_manifest,
    handle_validate_sensor,
)
from .parser import build_parser

COMMAND_HANDLERS: dict[str, Callable[..., int]] = {
    "show-layout": handle_show_layout,
    "list-sensors": handle_list_sensors,
    "list-planned-sensors": handle_list_planned_sensors,
    "list-bands": handle_list_bands,
    "show-metadata": handle_show_metadata,
    "show-response": handle_show_response,
    "validate-sensor": handle_validate_sensor,
    "export-validation": handle_export_validation,
    "validate-manifest": handle_validate_manifest,
    "show-registry-rows": handle_show_registry_rows,
    "register-manifest": handle_register_manifest,
    "register-planned-sensors": handle_register_planned_sensors,
}


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI."""

    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    handler = COMMAND_HANDLERS.get(args.command)
    if handler is None:
        parser.print_help()
        return 0
    return handler(args)
