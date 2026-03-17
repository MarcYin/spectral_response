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
python3 scripts/build/export_docs_visualization_assets.py --root .
python3 -m build
python3 -m twine check dist/*
mkdocs build --strict
```

## Refreshing visualization assets

The interactive docs page reads prebuilt JSON assets from `docs/assets/visualization/`. Refresh them whenever canonical sensor coverage changes:

```bash
python3 scripts/build/export_docs_visualization_assets.py --root .
```

## Repository conventions

- package code lives under `src/rsrf/`
- CLI wiring lives under `src/rsrf/commands/`
- parser implementations live under `src/rsrf/parsers/`
- canonical data and registries live under `data/`
- raw and extracted source artifacts live under `sources/`
- checked-in source manifests live under `sources/manifests/official/`
- planning catalogs live under `sources/manifests/planning/`
- manifest templates live under `sources/manifests/templates/`
- implementation history lives under `plans/`
- parser entrypoints live under `scripts/ingest/`
- QA entrypoints live under `scripts/validate/`

## Working with large source artifacts

The repo may contain large raw source files used for exact ingest. The PyPI distribution intentionally excludes repository data and raw artifacts, so release verification must happen from the repository checkout before packaging.
