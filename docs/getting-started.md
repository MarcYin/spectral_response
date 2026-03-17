# Getting Started

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

The code package and the canonical data repository are intentionally separate. Use one of these patterns:

```bash
export RSRF_ROOT=/path/to/spectral_response_function
```

```bash
rsrf list-sensors --root /path/to/spectral_response_function
```

If neither is supplied, RSRF searches upward from the current working directory for a repository root.

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
