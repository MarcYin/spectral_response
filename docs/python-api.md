# Python API

The `rsrf` package exports its public API from the top-level module. All functions listed here are available via `from rsrf import ...`.

## Sensor discovery

### `list_sensors`

```python
list_sensors(root: Path | None = None) -> list[dict[str, Any]]
```

List all registered sensor representations that have backing canonical artifacts on disk. Returns a list of dictionaries sorted by `sensor_unit_id` and `representation_variant`.

```python
from rsrf import list_sensors

sensors = list_sensors()
for s in sensors:
    print(s["sensor_unit_id"], s["representation_variant"], s["content_kind"])
```

### `list_bands`

```python
list_bands(
    sensor_unit_id: str,
    representation_variant: str | None = None,
    *,
    root: Path | None = None,
) -> list[dict[str, Any]]
```

List band-level registry rows for a sensor representation. When only one representation variant exists for the sensor, `representation_variant` can be omitted.

```python
from rsrf import list_bands

bands = list_bands("sentinel-2c_msi", "band_average")
for b in bands:
    print(b["band_id"], b.get("band_name"))
```

### `list_planned_sensors`

```python
list_planned_sensors(
    root: Path | None = None,
    *,
    catalog_path: Path | None = None,
) -> list[dict[str, Any]]
```

Return planned sensor entries from the planning catalog as JSON-friendly dictionaries. These are sensors tracked for future ingest that do not yet have canonical artifacts.

## Loading response definitions

### `load_response_definition`

```python
load_response_definition(
    sensor_unit_id: str,
    band_id: str,
    representation_variant: str | None = None,
    *,
    root: Path | None = None,
) -> SampledCurve | BandSpec
```

Load a canonical response definition for a single band. Returns a `SampledCurve` when the representation is `sampled_curve`, or a `BandSpec` when the representation is `band_spec`. This is the recommended general-purpose loading function.

```python
from rsrf import load_response_definition

response = load_response_definition("sentinel-2c_msi", "B03", "band_average")
print(type(response).__name__)  # SampledCurve
```

### `load_curve`

```python
load_curve(
    sensor_unit_id: str,
    band_id: str,
    representation_variant: str | None = None,
    *,
    root: Path | None = None,
) -> SampledCurve
```

Load a canonical sampled curve for a band. Raises `ValueError` if the representation is not `sampled_curve`.

```python
from rsrf import load_curve

curve = load_curve("sentinel-2c_msi", "B03", "band_average")
print(len(curve.wavelength_nm), "samples")
```

### `load_band_spec`

```python
load_band_spec(
    sensor_unit_id: str,
    band_id: str,
    representation_variant: str | None = None,
    *,
    root: Path | None = None,
) -> BandSpec
```

Load a canonical band specification for a band. Raises `ValueError` if the representation is not `band_spec`.

```python
from rsrf import load_band_spec

spec = load_band_spec("prisma_hsi", "B001", "metadata_band_spec")
print(spec.center_wavelength_nm, spec.fwhm_nm)
```

### `get_metadata`

```python
get_metadata(
    sensor_unit_id: str,
    representation_variant: str | None = None,
    *,
    root: Path | None = None,
) -> dict[str, Any]
```

Load the canonical `metadata.json` sidecar for a sensor representation.

```python
from rsrf import get_metadata

meta = get_metadata("sentinel-2c_msi", "band_average")
print(meta["content_kind"], meta["representation_variant"])
```

## Validation

### `validate_sensor`

```python
validate_sensor(
    sensor_unit_id: str,
    representation_variant: str | None = None,
    *,
    root: Path | None = None,
) -> dict[str, Any]
```

Validate a sensor representation and return a structured QA report. Dispatches to content-kind-specific validators for `sampled_curve` and `band_spec` representations.

### `validate_sampled_curve_inventory`

```python
validate_sampled_curve_inventory(
    *,
    root: Path | None = None,
) -> dict[str, Any]
```

Validate every `sampled_curve` representation in the repository and return an aggregate report.

### `write_validation_artifacts`

```python
write_validation_artifacts(
    sensor_unit_id: str,
    representation_variant: str | None = None,
    *,
    root: Path | None = None,
    output_dir: Path | None = None,
) -> dict[str, Path]
```

Run validation and write a `validation_report.json` and `overview.png` for a sensor representation. The output directory defaults to `docs/sensor-notes/<sensor>/<variant>/`.

## Manifests

### `resolve_manifest_path`

```python
resolve_manifest_path(
    path_or_name: str | Path,
    root: Path | None = None,
) -> Path
```

Resolve a manifest from an explicit path or a library filename. The resolution order is:

1. Absolute path (used as-is)
2. Relative path resolved from CWD (validated to be within the repo)
3. Relative to the repository root
4. Searched in the official, planning, and template manifest directories

Raises `FileNotFoundError` if no manifest is found.

### `manifest_path`

```python
manifest_path(
    root: Path | None,
    filename: str,
    *,
    manifest_group: str = "official",
) -> Path
```

Return the canonical filesystem path for a manifest in the requested group. Valid groups are `"official"`, `"planning"`, and `"templates"`.

### `iter_source_manifest_paths`

```python
iter_source_manifest_paths(
    root: Path | None = None,
    *,
    include_templates: bool = False,
    include_planning: bool = False,
) -> tuple[Path, ...]
```

Return all checked-in manifest JSON files in stable sorted order. By default only official manifests are included.

### `register_planned_sensor_catalog`

```python
register_planned_sensor_catalog(
    root: Path | None = None,
    *,
    catalog_path: Path | None = None,
) -> Path | None
```

Replace the planned slice of the sensor registry with entries from the planning catalog. Returns the path to the updated `sensors.parquet`, or `None` if no changes were needed.

## Curve realization

### `realize_curve`

```python
realize_curve(
    band_spec: BandSpec,
    *,
    profile_type: str = "gaussian",
    grid_policy: GridPolicy | None = None,
    normalization: str | None = "peak_1.0",
    source_variant: str | None = None,
) -> SampledCurve
```

Realize a sampled curve from a `BandSpec` by synthesizing response samples from the center wavelength and FWHM. Currently supports `gaussian` profile type with `peak_1.0` normalization and `adaptive_per_band` grid policies.

```python
from rsrf import load_band_spec, realize_curve

spec = load_band_spec("prisma_hsi", "B001", "metadata_band_spec")
curve = realize_curve(spec)
print(len(curve.wavelength_nm), "samples")
```

## Documentation site

### `prepare_docs_site`

```python
prepare_docs_site(
    root: Path | None = None,
    *,
    refresh_visualization_data: bool = True,
) -> dict[str, Path]
```

Render generated docs files, sync versioned JS/CSS visualization bundles, and optionally refresh the visualization data assets. Returns a dictionary of output paths.

### `export_docs_visualization_assets`

```python
export_docs_visualization_assets(
    root: Path | None = None,
    *,
    output_dir: Path | None = None,
    sensor_keys: Iterable[tuple[str, str]] | None = None,
) -> dict[str, Path]
```

Export interactive documentation visualization assets (JSON sensor data files) for the MkDocs site.

## Common parameters

All repository-aware functions accept an optional `root` parameter:

| Parameter | Type | Description |
|-----------|------|-------------|
| `root` | `Path \| None` | Repository root path. When `None`, resolved via `RSRF_ROOT` environment variable or upward directory walk from CWD. |

## Data classes

The loading functions return frozen dataclass instances. See the [Data Model](data-model.md) page for field-level documentation of `BandSpec`, `SampledCurve`, and the `ContentKind` enum.
