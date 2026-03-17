# RSRF

`RSRF` is a repository-backed Python toolkit for canonical optical sensor spectral response definitions.

It combines three things that usually drift apart:

- a clean Python API for reading sampled curves and metadata-only band specs
- reproducible ingest tooling for official upstream response artifacts
- QA and release workflows for maintaining a curated response repository

The PyPI distribution name is `RSRF`. The import package is `rsrf`.

## Installation

During development:

```bash
python3 -m pip install -e ".[dev]"
```

After release:

```bash
python3 -m pip install RSRF
```

## Quick start

From a repository checkout:

```bash
export RSRF_ROOT="$PWD"
rsrf list-sensors
rsrf list-bands sentinel-2c_msi --variant band_average
rsrf show-response prisma_hsi B001 --variant metadata_band_spec
rsrf validate-sensor sentinel-2c_msi --variant band_average
```

From Python:

```python
from rsrf import list_sensors, load_response_definition

sensors = list_sensors()
response = load_response_definition("sentinel-2c_msi", "B01", "band_average")
```

## Working with repository data

The installed package does not bundle the full canonical repository, raw sources, or parquet registries. Point the code at a repository checkout or generated data root with one of these patterns:

- run commands from the repository root
- pass `--root /path/to/repo`
- set `RSRF_ROOT=/path/to/repo`

Manifest-driven commands also resolve checked-in manifest filenames directly from the manifest library, so this works from the repository root:

```bash
rsrf validate-manifest rsrf_source_manifest_sentinel2c_v2.json
rsrf register-manifest rsrf_source_manifest_prisma_hsi_v2.json
```

## Repository structure

```text
.
|-- data/
|   |-- canonical/
|   |-- common_grid/
|   |-- realized/
|   `-- registry/
|-- docs/
|-- plans/
|-- scripts/
|   |-- build/
|   |-- ingest/
|   `-- validate/
|-- sources/
|   |-- extracted/
|   |-- manifests/
|   |   |-- official/
|   |   |-- planning/
|   |   `-- templates/
|   `-- raw/
|-- src/rsrf/
|   |-- commands/
|   `-- parsers/
`-- tests/
```

The package is organized so users can navigate by concern:

- `src/rsrf/api.py`: read-side access to canonical sensor definitions
- `src/rsrf/commands/`: CLI parser, dispatch, and output helpers
- `src/rsrf/ingest.py`: canonical artifact writing and registry updates
- `src/rsrf/manifests.py`: manifest library lookup and path resolution
- `src/rsrf/parsers/`: sensor-family-specific source parsers
- `src/rsrf/planning.py`: registry-first planning catalog support
- `src/rsrf/qa.py`: validation reports and plot export
- `src/rsrf/registry.py`: repository layout and parquet registry helpers

Trusted sampled-curve overlays live at:

```text
sources/extracted/<sensor_unit_id>/<representation_variant>/overlay_reference.csv
```

## Current coverage

The repository currently includes:

- sampled-curve families across Sentinel-2, Landsat MSS/TM/ETM+/OLI/TIRS, MODIS, VIIRS, OLCI, ASTER, Planet, PROBA-V, and legacy NASA OBPG ocean-colour missions
- band-spec families across PACE OCI, EnMAP, EMIT, PRISMA, Satellogic NewSat, Pleiades, Pleiades-Neo, SPOT-6/7, FORMOSAT-5, Amazonia-1, and CBERS-4A
- optional realized Gaussian approximations when official full sampled curves are not published

The remaining notable gap from the original roadmap is `DESIS`.

## Documentation

Project documentation is built with MkDocs:

- [https://marcyin.github.io/spectral_response/](https://marcyin.github.io/spectral_response/)

Key entry points:

- getting started: [`docs/getting-started.md`](docs/getting-started.md)
- interactive visualizations: [https://marcyin.github.io/spectral_response/visualizations/](https://marcyin.github.io/spectral_response/visualizations/) ([`docs/visualizations.md`](docs/visualizations.md))
- repository layout: [`docs/repository-layout.md`](docs/repository-layout.md)
- CLI reference: [`docs/cli.md`](docs/cli.md)
- data model: [`docs/data-model.md`](docs/data-model.md)
- development guide: [`docs/development.md`](docs/development.md)
- release guide: [`docs/releasing.md`](docs/releasing.md)

## Development

Run the local verification stack with:

```bash
python3 -m unittest discover -s tests/unit
python3 -m unittest discover -s tests/regression
python3 scripts/build/export_docs_visualization_assets.py --root .
python3 -m build
python3 -m twine check dist/*
mkdocs build --strict
```

## Project status

The active design and implementation history now live under `plans/`:

- [`plans/rsrf_repo_plan_v3_hyperspectral_support.md`](plans/rsrf_repo_plan_v3_hyperspectral_support.md)
- [`plans/rsrf_implementation_plan.md`](plans/rsrf_implementation_plan.md)
