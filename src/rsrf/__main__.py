"""Module entrypoint for ``python -m rsrf``."""

from .commands.app import main

if __name__ == "__main__":
    raise SystemExit(main())
