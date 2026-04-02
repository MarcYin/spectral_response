# CLI Reference

The `rsrf` CLI is the main operator interface for repository inspection and QA.

## Global options

| Option | Description |
|--------|-------------|
| `--version` | Print the RSRF version and exit |
| `--root PATH` | Repository root directory. Defaults to `RSRF_ROOT` or upward directory search |

## Discovery commands

### `show-layout`

Print the repository directory layout and resolved paths.

```bash
rsrf show-layout
```

### `list-sensors`

List all registered sensor representations that have backing canonical artifacts.

```bash
rsrf list-sensors
```

### `list-planned-sensors`

List registry-first planned sensor representations from the planning catalog.

```bash
rsrf list-planned-sensors
rsrf list-planned-sensors --catalog-path /path/to/custom_catalog.json
```

| Option | Description |
|--------|-------------|
| `--catalog-path PATH` | Override the default planning catalog path |

### `list-bands`

List canonical band rows for a sensor representation.

```bash
rsrf list-bands sentinel-2c_msi --variant band_average
```

| Argument | Description |
|----------|-------------|
| `sensor_unit_id` | Sensor identifier (positional, required) |
| `--variant` | Representation variant; required when multiple variants exist |

## Metadata and response inspection

### `show-metadata`

Print the canonical `metadata.json` sidecar for a sensor representation.

```bash
rsrf show-metadata hyperspec_example --variant metadata_band_spec
rsrf show-metadata sentinel-2c_msi --variant band_average
```

| Argument | Description |
|----------|-------------|
| `sensor_unit_id` | Sensor identifier (positional, required) |
| `--variant` | Representation variant |

### `show-response`

Print a compact band-level response summary (sampled curve samples or band spec parameters).

```bash
rsrf show-response sentinel-2c_msi B03 --variant band_average
rsrf show-response prisma_hsi B001 --variant metadata_band_spec
```

| Argument | Description |
|----------|-------------|
| `sensor_unit_id` | Sensor identifier (positional, required) |
| `band_id` | Band identifier (positional, required) |
| `--variant` | Representation variant |

## Validation commands

### `validate-sensor`

Validate a sensor representation and print the structured QA report.

```bash
rsrf validate-sensor sentinel-2c_msi --variant band_average
```

| Argument | Description |
|----------|-------------|
| `sensor_unit_id` | Sensor identifier (positional, required) |
| `--variant` | Representation variant |

### `export-validation`

Write a `validation_report.json` and `overview.png` for a sensor representation.

```bash
rsrf export-validation hyperspec_example --variant metadata_band_spec
rsrf export-validation sentinel-2c_msi --variant band_average --output-dir /tmp/rsrf_validation
```

| Argument | Description |
|----------|-------------|
| `sensor_unit_id` | Sensor identifier (positional, required) |
| `--variant` | Representation variant |
| `--output-dir PATH` | Directory for validation artifacts; defaults to `docs/sensor-notes/<sensor>/<variant>/` |

### `validate-manifest`

Validate a source manifest JSON file against the typed manifest model.

```bash
rsrf validate-manifest rsrf_source_manifest_sentinel2c_v2.json
```

| Argument | Description |
|----------|-------------|
| `manifest_path` | Path or library filename of the manifest (positional, required) |

Manifest filenames are resolved from the manifest library, so you usually do not need the full `sources/manifests/official/...` path.

## Registry operations

### `show-registry-rows`

Print the registry rows that would be derived from a manifest.

```bash
rsrf show-registry-rows rsrf_source_manifest_prisma_hsi_v2.json
```

| Argument | Description |
|----------|-------------|
| `manifest_path` | Path or library filename of the manifest (positional, required) |

### `register-manifest`

Upsert manifest-derived rows into the `data/registry/` parquet tables.

```bash
rsrf register-manifest rsrf_source_manifest_prisma_hsi_v2.json
```

| Argument | Description |
|----------|-------------|
| `manifest_path` | Path or library filename of the manifest (positional, required) |

### `register-planned-sensors`

Upsert planned sensor rows from the planning catalog into `sensors.parquet`.

```bash
rsrf register-planned-sensors
rsrf register-planned-sensors --catalog-path /path/to/custom_catalog.json
```

| Option | Description |
|--------|-------------|
| `--catalog-path PATH` | Override the default planning catalog path |

## Root selection

All repository-aware commands accept `--root`. For installed-package workflows, setting `RSRF_ROOT` is usually the simplest option:

```bash
export RSRF_ROOT=/path/to/spectral_response_function
rsrf list-sensors
```

If neither `--root` nor `RSRF_ROOT` is provided, RSRF searches upward from the current working directory for a repository root.
