# Getting Started

RSRF requires Python 3.9 or later (tested up to 3.14).

## Installation

During development:

```bash
python3 -m pip install -e ".[dev]"
```

For a release install, the target distribution name is:

```bash
python3 -m pip install RSRF
```

## Pointing RSRF at repository data

The wheel does not embed the full repository snapshot. Instead, RSRF resolves the active root in this order:

1. **Explicit argument**: pass `root=` to Python functions or `--root` to CLI commands
2. **Environment variable**: set `RSRF_ROOT`
3. **Auto-discovery**: RSRF walks upward from the current working directory
4. **Release bootstrap**: outside a checkout, RSRF downloads the matching GitHub release snapshot into a local cache

For most workflows, running commands from the repository checkout is sufficient. For installed-package or notebook workflows, the default release bootstrap is usually enough. Set the environment variable only when you want to override that default:

```bash
export RSRF_ROOT=/path/to/spectral_response_function
```

## Working with manifests

Manifest-aware commands accept either explicit paths or manifest filenames from the checked-in manifest library:

```bash
rsrf validate-manifest rsrf_source_manifest_sentinel2c_v2.json
rsrf show-registry-rows rsrf_source_manifest_prisma_hsi_v2.json
```

Checked-in manifests live under `sources/manifests/official/`, planning catalogs under `sources/manifests/planning/`, and templates under `sources/manifests/templates/`.

## First commands

```bash
rsrf --help
rsrf list-sensors
rsrf list-bands sentinel-2c_msi --variant band_average
rsrf show-response prisma_hsi B001 --variant metadata_band_spec
rsrf show-metadata hyperspec_example --variant metadata_band_spec
rsrf validate-sensor sentinel-2c_msi --variant band_average
```

## First Python session

```python
from rsrf import list_sensors, load_response_definition

print(list_sensors()[:3])
response = load_response_definition("sentinel-2c_msi", "B01", "band_average")
print(type(response).__name__)
```

## Error handling

Loading functions raise predictable exceptions:

```python
from rsrf import load_curve, load_response_definition

# KeyError when a sensor or band is not found
try:
    load_curve("nonexistent_sensor", "B01")
except KeyError as exc:
    print(f"Not found: {exc}")

# ValueError when the content kind does not match the loader
try:
    load_curve("prisma_hsi", "B001", "metadata_band_spec")  # band_spec, not sampled_curve
except ValueError as exc:
    print(f"Wrong content kind: {exc}")
```

`validate_sensor()` does not raise on validation failures; it returns a structured report dictionary with pass/fail status and diagnostic messages.

## Next steps

- [Python API](python-api.md) for the full function reference
- [CLI Reference](cli.md) for all available commands
- [Data Model](data-model.md) for `BandSpec`, `SampledCurve`, and registry table details
- [Visualizations](visualizations.md) for interactive spectral response plots
