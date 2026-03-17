# RSRF

`RSRF` is a Python toolkit and repository layout for canonical spectral response definitions for optical satellite sensors.

It provides:

- a registry-backed read API for sampled curves and metadata-only band specs
- ingest tooling for official source artifacts
- QA reporting and validation plots
- a CLI for discovery, inspection, and release workflows

The distribution name is `RSRF`. The import package is `rsrf`.

## What ships in the package

The PyPI package is code-focused. It does not bundle the full canonical data repository, raw source files, or large parquet registries. Install the package to get the API, CLI, ingest logic, QA helpers, and release tooling.

To work against a repository checkout or a generated data root, either:

- run commands from the repository root
- pass `--root /path/to/repo`
- set `RSRF_ROOT=/path/to/repo`

## Current coverage

The repository currently covers:

- sampled-curve families including Sentinel-2, Landsat MSS/TM/ETM+/OLI/TIRS, MODIS, VIIRS, OLCI, ASTER, legacy NASA OBPG ocean-colour sensors, Planet RSR families, and PROBA-V
- band-spec families including PACE OCI, EnMAP, EMIT, PRISMA, Satellogic NewSat, Pleiades, Pleiades-Neo, SPOT-6/7, FORMOSAT-5, Amazonia-1, and CBERS-4A
- realized Gaussian approximations for metadata-only sources when official full curves are not published

The remaining notable gap in the original roadmap is `DESIS`.

## Installation

Install from source during development:

```bash
python3 -m pip install -e ".[dev]"
```

Once the project is published to PyPI, the intended install command is:

```bash
python3 -m pip install RSRF
```

## Quick start

From a repository checkout:

```bash
export RSRF_ROOT="$PWD"
rsrf --help
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

## Repository layout

```text
.
|-- data/
|   |-- canonical/
|   |-- common_grid/
|   |-- realized/
|   `-- registry/
|-- docs/
|-- scripts/
|-- sources/
|-- src/rsrf/
`-- tests/
```

Trusted sampled-curve overlays live at:

```text
sources/extracted/<sensor_unit_id>/<representation_variant>/overlay_reference.csv
```

## Documentation

Documentation source lives in `docs/` and is built with MkDocs. The intended published site URL is:

- [https://marcyin.github.io/spectral_response/](https://marcyin.github.io/spectral_response/)

Key pages:

- getting started: [`docs/getting-started.md`](docs/getting-started.md)
- CLI reference: [`docs/cli.md`](docs/cli.md)
- data model: [`docs/data-model.md`](docs/data-model.md)
- release guide: [`docs/releasing.md`](docs/releasing.md)

## Development

Run the full local validation stack with:

```bash
python3 -m unittest discover -s tests/unit
python3 -m unittest discover -s tests/regression
python3 -m build
python3 -m twine check dist/*
mkdocs build --strict
```

GitHub Actions workflows are provided for:

- CI on pushes and pull requests
- GitHub Pages docs deployment
- PyPI publishing via trusted publishing

## Project status

The active design baseline and implementation history are still tracked in:

- [`rsrf_repo_plan_v3_hyperspectral_support.md`](rsrf_repo_plan_v3_hyperspectral_support.md)
- [`rsrf_implementation_plan.md`](rsrf_implementation_plan.md)
