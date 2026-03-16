"""IO helpers used across the repository."""

from __future__ import annotations

import importlib.util
import json
import hashlib
from pathlib import Path
from typing import Any, Mapping, Sequence


def ensure_directory(path: Path) -> Path:
    """Create a directory and return it."""

    path.mkdir(parents=True, exist_ok=True)
    return path


def read_json(path: Path) -> Any:
    """Read a JSON file."""

    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: Mapping[str, Any]) -> Path:
    """Write a JSON document using stable formatting."""

    ensure_directory(path.parent)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return path


def file_sha256(path: Path) -> str:
    """Compute the SHA-256 digest for a file."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parquet_engine() -> str | None:
    """Return the available parquet engine name, if any."""

    if importlib.util.find_spec("pyarrow") is not None:
        return "pyarrow"
    if importlib.util.find_spec("fastparquet") is not None:
        return "fastparquet"
    return None


def parquet_support_available() -> bool:
    """Report whether parquet read/write support is available."""

    try:
        import pandas  # noqa: F401
    except ImportError:
        return False
    return parquet_engine() is not None


def dataframe_from_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    columns: Sequence[str] | None = None,
):
    """Build a DataFrame from row mappings."""

    try:
        import pandas as pd
    except ImportError as exc:
        raise RuntimeError("pandas is required for table IO") from exc

    frame = pd.DataFrame(list(rows))
    if columns is not None:
        frame = frame.reindex(columns=list(columns))
    return frame


def write_parquet_table(
    path: Path,
    rows: Sequence[Mapping[str, Any]],
    *,
    columns: Sequence[str] | None = None,
):
    """Write a parquet table from row mappings."""

    engine = parquet_engine()
    if engine is None:
        raise RuntimeError(
            "Parquet support requires either pyarrow or fastparquet in the Python environment"
        )

    frame = dataframe_from_rows(rows, columns=columns)
    ensure_directory(path.parent)
    frame.to_parquet(path, index=False, engine=engine)
    return path


def read_parquet_table(path: Path):
    """Read a parquet table into a DataFrame."""

    engine = parquet_engine()
    if engine is None:
        raise RuntimeError(
            "Parquet support requires either pyarrow or fastparquet in the Python environment"
        )

    try:
        import pandas as pd
    except ImportError as exc:
        raise RuntimeError("pandas is required for table IO") from exc

    return pd.read_parquet(path, engine=engine)


def upsert_parquet_table(
    path: Path,
    rows: Sequence[Mapping[str, Any]],
    *,
    key_columns: Sequence[str],
    columns: Sequence[str] | None = None,
):
    """Upsert rows into a parquet-backed table using a simple key-based merge."""

    try:
        import pandas as pd
    except ImportError as exc:
        raise RuntimeError("pandas is required for table IO") from exc

    incoming = dataframe_from_rows(rows, columns=columns)
    if path.exists():
        existing = read_parquet_table(path)
        frames = [
            frame.dropna(axis=1, how="all")
            for frame in (existing, incoming)
        ]
        combined = pd.concat(frames, ignore_index=True, sort=False)
    else:
        combined = incoming

    if key_columns:
        combined = combined.drop_duplicates(subset=list(key_columns), keep="last")
    if columns is not None:
        combined = combined.reindex(columns=list(columns))

    engine = parquet_engine()
    if engine is None:
        raise RuntimeError(
            "Parquet support requires either pyarrow or fastparquet in the Python environment"
        )
    ensure_directory(path.parent)
    combined.to_parquet(path, index=False, engine=engine)
    return path
