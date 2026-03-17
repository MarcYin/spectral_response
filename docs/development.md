# Development

## Editable install

```bash
python3 -m pip install -e ".[dev]"
```

## Local verification

Run the same core commands used by CI:

```bash
python3 -m unittest discover -s tests/unit
python3 -m unittest discover -s tests/regression
python3 -m build
python3 -m twine check dist/*
mkdocs build --strict
```

## Repository conventions

- package code lives under `src/rsrf/`
- canonical data and registries live under `data/`
- raw and extracted source artifacts live under `sources/`
- parser entrypoints live under `scripts/ingest/`
- QA entrypoints live under `scripts/validate/`

## Working with large source artifacts

The repo may contain large raw source files used for exact ingest. The PyPI distribution intentionally excludes repository data and raw artifacts, so release verification must happen from the repository checkout before packaging.
