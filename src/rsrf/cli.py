"""Compatibility wrapper for the CLI entrypoint."""

from .commands.app import main
from .commands.parser import build_parser

__all__ = ["build_parser", "main"]
