# Data Model

## Canonical forms

RSRF stores optical response definitions in two canonical forms, identified by the `ContentKind` enum.

### `ContentKind`

| Value | Description |
|-------|-------------|
| `sampled_curve` | Full spectral response samples on a wavelength axis |
| `band_spec` | Metadata-only band parameters (center wavelength, FWHM, etc.) |
| `hybrid` | Reserved for manifests that produce both sampled curves and band specs |

## `sampled_curve`

Use `sampled_curve` when the official source publishes explicit response samples on a wavelength axis.

Typical artifacts:

- `curves.parquet`
- `metadata.json`

Typical examples:

- Sentinel-2 MSI
- Landsat OLI/TIRS
- MODIS
- VIIRS
- Planet RSR CSV families

### `SampledCurve` fields

The `SampledCurve` dataclass (frozen) is returned by `load_curve()` and `load_response_definition()`:

| Field | Type | Description |
|-------|------|-------------|
| `band_id` | `str` | Band identifier (e.g. `"B03"`, `"B001"`) |
| `wavelength_nm` | `Sequence[float]` | Wavelength samples in nanometers, sorted ascending |
| `response` | `Sequence[float]` | Response values corresponding to each wavelength sample |
| `source_variant` | `str \| None` | Representation variant that produced this curve, or `None` |

## `band_spec`

Use `band_spec` when the official source only publishes band parameters such as:

- center wavelength
- FWHM
- support interval
- quality flags

Typical artifacts:

- `band_specs.parquet`
- `metadata.json`

Typical examples:

- EnMAP
- EMIT
- PRISMA
- PACE OCI
- WMO OSCAR support-range proxies

### `BandSpec` fields

The `BandSpec` dataclass (frozen) is returned by `load_band_spec()` and `load_response_definition()`:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `band_id` | `str` | required | Band identifier |
| `center_wavelength_nm` | `float` | required | Center wavelength in nanometers |
| `fwhm_nm` | `float` | required | Full width at half maximum in nanometers |
| `band_index` | `int \| None` | `None` | Numeric band ordering index |
| `band_name` | `str \| None` | `None` | Human-readable band name |
| `band_status` | `str` | `"nominal"` | Quality or operational status flag |
| `published_shape_type` | `str` | `"unknown"` | Shape type from the source (e.g. `"gaussian"`, `"tabulated"`) |
| `shape_param_json` | `Mapping[str, Any]` | `{}` | Additional shape parameters as key-value pairs |

## Realized curves

Some `band_spec` sources can optionally produce derived sampled curves under `data/realized/`. These are approximations synthesized from center wavelength and FWHM using a profile model (typically Gaussian), not replacements for native published SRFs.

Realized curves are produced by the `realize_curve()` function and controlled by the `CurveRealizationSpec` section in source manifests.

## Sensor definitions

RSRF also exposes a versioned whole-sensor interchange model for downstream packages and custom user inputs.

### `SensorDefinition` fields

The `SensorDefinition` dataclass (frozen) is returned by `get_sensor_definition()`, `coerce_sensor_definition()`, and `load_sensor_definition()`:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `schema_type` | `str` | `"rsrf_sensor_definition"` | Public schema identifier |
| `schema_version` | `str` | `"1.0.0"` | Version of the serialized sensor-definition contract |
| `sensor_id` | `str` | required | Stable sensor identifier |
| `bands` | `tuple[BandDefinition, ...]` | required | Ordered per-band definitions |
| `extensions` | `Mapping[str, Any]` | `{}` | Namespaced metadata preserved through round-trip serialization |

### `BandDefinition` fields

Each `BandDefinition` holds the downstream-facing band payload:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `band_id` | `str` | required | Unique band identifier within the sensor |
| `response_definition` | `Mapping[str, Any]` | required | Stable JSON-shaped response definition with `kind="sampled"` and center/FWHM forms represented as `kind="band_spec"` or `kind="gaussian"` |
| `extensions` | `Mapping[str, Any]` | `{}` | Namespaced band metadata |

### Extensions

Known downstream metadata lives under `extensions.<consumer_name>`. The initial validated extension namespace is:

- `extensions.spectral_library.segment`

Allowed `segment` values are:

- `vnir`
- `swir`

Unknown extension namespaces are preserved, but the `spectral_library` block is validated strictly.

## Registry tables

The repository registry lives under `data/registry/`:

| Table | Description |
|-------|-------------|
| `sensors.parquet` | Sensor representations with mission, platform, instrument, and content kind |
| `bands.parquet` | Band-level rows with band IDs, names, indices, and wavelength metadata |
| `sources.parquet` | Source provenance rows linked to manifests |
| `band_specs.parquet` | Band specification parameter rows for `band_spec` representations |
| `realizations.parquet` | Tracking rows for realized (approximated) sampled curves |

These tables drive the public read API and the CLI.

## Repository root resolution

Repository-aware operations resolve the root in this order:

1. explicit `root=` argument or `--root`
2. `RSRF_ROOT` environment variable
3. upward search from the current working directory
4. cached GitHub release snapshot for the installed version
