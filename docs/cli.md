# CLI Reference

The `rsrf` CLI is the main operator interface for repository inspection and QA.

## Discovery

```bash
rsrf show-layout
rsrf list-sensors
rsrf list-planned-sensors
rsrf list-bands sentinel-2c_msi --variant band_average
```

## Metadata and response inspection

```bash
rsrf show-metadata hyperspec_example --variant metadata_band_spec
rsrf show-response sentinel-2c_msi B03 --variant band_average
rsrf show-response prisma_hsi B001 --variant metadata_band_spec
```

## Validation

```bash
rsrf validate-manifest rsrf_source_manifest_sentinel2c_v2.json
rsrf validate-sensor sentinel-2c_msi --variant band_average
rsrf export-validation hyperspec_example --variant metadata_band_spec --output-dir /tmp/rsrf_validation
```

Manifest filenames are resolved from the manifest library, so you usually do not need the full `sources/manifests/official/...` path.

## Registry operations

```bash
rsrf show-registry-rows rsrf_source_manifest_prisma_hsi_v2.json
rsrf register-manifest rsrf_source_manifest_prisma_hsi_v2.json
rsrf register-planned-sensors
```

## Root selection

All repository-aware commands accept `--root`. For installed-package workflows, `RSRF_ROOT` is usually the simplest option.
