# Relative Spectral Response Function (RSRF) repository plan v2

## 1. Goal

Build a reproducible, versioned repository and Python package that provides **relative spectral response functions (RSFs / RSRs / SRFs)** for spaceborne optical sensors, together with enough provenance and metadata to support:

- spectral simulation
- bandpass convolution
- sensor harmonization / cross-walking
- QA and reproducible ingest pipelines

This version improves the earlier plan by making the data model stricter, adding source-quality tiers, and separating canonical from derived products.

---

## 2. Scope and non-goals

### 2.1 In-scope for v1

Spaceborne sensors with bands in at least one of:
- UV / VIS / NIR / SWIR
- TIR, **if** an official or high-quality alternative SRF exists

### 2.2 Priority families

#### P0 — highest value, strong public sources
- Landsat MSS / TM / ETM+ / OLI / TIRS
- Sentinel-2 MSI: **S2A, S2B, S2C**
- MODIS: Terra, Aqua
- VIIRS: SNPP, NOAA-20, NOAA-21
- Sentinel-3 OLCI: S3A, S3B
- ASTER

#### P1 — strong scientific value, some metadata-driven handling
- PACE OCI
- EnMAP
- DESIS
- EMIT
- PROBA-V
- ocean-colour legacy sensors via NASA OBPG curated tables

#### P2 — partial / gated / vendor-doc driven
- PRISMA
- PlanetScope: PS2, PS2.SD, PSB.SD
- RapidEye
- SkySat
- Pléiades / Pléiades Neo / SPOT families
- Satellogic NewSat
- Amazonia-1, CBERS-4A, Formosat-5, and similar regional missions

### 2.3 Explicit non-goals for v1
- deriving physics-grade SRFs from only brochure band centers without strong documentation
- mixing approximate Gaussian curves with official curves without clear labeling
- hiding thermal bands by forcing everything into 300–2500 nm only

---

## 3. Core design decision

## Canonical storage must be native-support, not dense 300–2500 nm only.

Why:
- Many sensors have **thermal bands beyond 2500 nm**.
- Some sources provide detector-/camera-/pixel-dependent SRFs.
- Dense common grids are convenient for users, but they are a **derived product**, not the scientific source of truth.

### 3.1 Recommended two-layer design

#### Layer A — canonical (`native`)
Store each SRF on its native wavelength support, or on the source-provided wavelength axis, trimmed only after explicit QA.

#### Layer B — derived (`common_grid`)
Generate convenience products on fixed grids, e.g.:
- `reflective_300_2500_1nm`
- `reflective_300_2500_0p1nm` for ocean-colour / narrowband work
- `tir_2500_14000_1nm`
- optional combined `vswir_tir_380_14000_1nm`

### 3.2 Canonical normalization policy

Store curves as **relative response in [0, 1]**, preserving the published shape. Do **not** force area-normalization in storage.

Use runtime normalization for convolution:

```text
L_band = sum(L_i * R_i * dλ_i) / sum(R_i * dλ_i)
```

This keeps the canonical data simple and faithful to source publications.

---

## 4. Source quality tiers

Every sensor/band entry must have a `source_tier`.

### Tier A — official downloadable SRF/RSR
Examples:
- official Excel / CSV / text tables
- official mission web pages with downloadable SRF data

### Tier B — official metadata-based SRF
Examples:
- per-product metadata contains SRF or enough per-band spectral-response detail
- official PDF/XLSX with extractable curves but no direct machine-readable table

### Tier C — official landing page only
Examples:
- official docs expose band centers/FWHM but not full curves

### Tier D — trusted alternative curated source
Examples:
- NASA OBPG curated SRF tables
- NWP SAF SRF catalogue
- USGS Spectral Characteristics Viewer

### Tier E — documented approximation
Examples:
- Gaussian reconstructed from official center wavelength + FWHM
- literature-derived reconstruction when no official full curve is public

### Policy
- `A`, `B`, and `D` can be published in the main dataset.
- `C` stays in the registry but is **not ingest-complete**.
- `E` can be published only if explicitly labeled `approximation=true` and separated from official curves.

---

## 5. Sensor identity model

The first plan was too mission-centric. The registry should be **sensor-unit-centric**.

Use three levels:

1. **mission family** — e.g. `sentinel-2`
2. **sensor unit** — e.g. `sentinel-2c_msi`
3. **representation variant** — e.g. `band_average`, `camera_column`, `product_order`, `sensor_order`, `metadata_average`, `gaussian_approx`

### Example IDs
- `landsat-9_oli-2.band-average.B05`
- `sentinel-2c_msi.band-average.B08`
- `sentinel-3b_olci.camera-column.Oa08`
- `viirs_noaa21.product-order.M05`
- `desis_iss.metadata-average.B123`

This avoids losing distinctions such as:
- S2A vs S2B vs S2C
- SNPP vs NOAA-20 vs NOAA-21 VIIRS
- OLCI-A vs OLCI-B
- detector-order vs product-order variants

---

## 6. Recommended repository structure

```text
repo/
  README.md
  pyproject.toml
  src/rsrf/
    registry.py
    io.py
    resample.py
    convolve.py
    validate.py
    plotting.py
  data/
    registry/
      sensors.parquet
      bands.parquet
      sources.parquet
    native/
      <sensor_unit>/<representation_variant>/curves.parquet
      <sensor_unit>/<representation_variant>/metadata.json
    common_grid/
      reflective_300_2500_1nm/<sensor_unit>.nc
      reflective_300_2500_0p1nm/<sensor_unit>.nc
      tir_2500_14000_1nm/<sensor_unit>.nc
  sources/
    raw/
      <agency>/<mission>/<platform>/<instrument>/<doc_version>/...
    extracted/
      <sensor_unit>/<representation_variant>/...
    manifests/
      source_manifest.jsonl
  scripts/
    ingest/
    validate/
    build/
  tests/
    data/
    unit/
    regression/
  docs/
    decisions/
    sensor-notes/
```

### Why this is better
- `parquet` is efficient for long-form curves and metadata tables.
- `netCDF` is better for dense common-grid products.
- raw sources and extracted outputs stay separate.

---

## 7. Data model

## 7.1 Registry tables

### `sensors.parquet`
One row per sensor unit / representation variant.

Suggested fields:
- `sensor_unit_id`
- `mission_family`
- `platform`
- `instrument`
- `representation_variant`
- `spectral_domain`
- `source_tier`
- `approximation`
- `official_source_available`
- `license_note`
- `status` (`planned`, `registered`, `ingested`, `validated`, `released`)

### `bands.parquet`
One row per band.

Suggested fields:
- `sensor_unit_id`
- `band_id`
- `band_name`
- `center_wavelength_nm`
- `fwhm_nm`
- `native_support_min_nm`
- `native_support_max_nm`
- `native_sampling_nm`
- `normalization`
- `has_nonzero_curve`

### `sources.parquet`
One row per source artifact.

Suggested fields:
- `source_id`
- `sensor_unit_id`
- `source_tier`
- `source_type` (`official`, `official_metadata`, `alternative`, `literature`)
- `title`
- `url`
- `retrieved_at`
- `file_sha256`
- `doc_version`
- `notes`

## 7.2 Curve storage (`curves.parquet`)

Use a long-form table:
- `sensor_unit_id`
- `representation_variant`
- `band_id`
- `wavelength_nm`
- `response`
- `is_native`
- `is_trimmed`
- `source_id`

This avoids awkward nested arrays and keeps the data easy to query in pandas / polars / DuckDB.

---

## 8. Normalization, trimming, and zero policy

The earlier plan did not fully define zero handling. Add explicit rules.

### 8.1 Published axis first
Do not invent a new wavelength axis for canonical storage if the source already provides one.

### 8.2 Trimming
For canonical storage:
- preserve source support when available
- optionally store a trimmed copy with `epsilon_zero_threshold`
- trimming rule must be recorded in metadata

### 8.3 Zero policy
- clip tiny negative numeric artifacts to zero
- record the threshold used
- preserve interior zeros
- do not smooth source curves unless a separate derived representation is being created

### 8.4 Approximation policy
If only center wavelength and FWHM exist:
- create `gaussian_approx` only in a separate variant
- require `approximation=true`
- never silently merge approximations with official curves

---

## 9. Validation pipeline

A sensor is not “done” when the file is downloaded. It is done when it passes QA.

### 9.1 Automated checks
- wavelengths strictly increasing within each band
- no duplicate `(band_id, wavelength_nm)` pairs
- response values finite and >= 0
- maximum response > 0
- support range recorded and consistent
- expected band count matches source
- checksum present for raw source file

### 9.2 Scientific QA
- overlay plots against source figure or alternative trusted source
- compare center and FWHM derived from ingested curve vs documented values
- compare common-grid resampling integrals vs native curve integrals
- flag suspicious multi-peak or truncated shapes

### 9.3 Release gates
Minimum release criteria for a sensor unit:
- raw source archived
- parser script committed
- metadata complete
- automated tests passing
- validation plot generated
- source tier assigned

---

## 10. Package API suggestions

The repository should power a small but stable Python API.

### 10.1 Read API
- `list_sensors()`
- `list_bands(sensor_unit_id)`
- `get_metadata(sensor_unit_id)`
- `load_curve(sensor_unit_id, band_id, variant="native")`

### 10.2 Processing API
- `resample_curve(curve, grid_nm)`
- `build_common_grid(sensor_unit_id, grid_spec)`
- `convolution_weights(curve, spectrum_grid_nm)`
- `convolve_spectrum(spectrum, curve)`
- `effective_wavelength(curve, weighting="flat")`

### 10.3 Discovery API
- `find_equivalent_bands(sensor_a, sensor_b)`
- `registry_search(mission=None, domain=None, source_tier=None)`

---

## 11. Recommended initial source map

### P0 ingest now
- **USGS Spectral Characteristics Viewer** for Landsat family and additional bootstrap sensors
- **Copernicus / SentiWiki** for Sentinel-2 SRF files, including S2C
- **MCST** for MODIS Terra/Aqua RSR tables
- **NOAA NCC** for VIIRS SNPP / NOAA-20 / NOAA-21 RSRs
- **official Sentinel-3 docs** for OLCI and SLSTR
- **ASTER JPL mission pages** for VNIR / SWIR / TIR response data

### P1 ingest after schema is stable
- **NASA OBPG SRF tables** for ocean-colour and curated cross-checks
- **PACE OCI characterization pages**
- **EnMAP spectral bands update workbook**
- **DESIS metadata / STAC / workshop notes**
- **EMIT spectral properties pages**
- **PROBA-V docs**

### P2 registry-first, ingest later
- **PRISMA** official portal and acquisition catalogue
- **Planet docs** for PlanetScope / RapidEye / SkySat
- **Airbus** resource-center docs for Pléiades / SPOT families
- vendor/regional missions with only landing pages or partial specs

---

## 12. Governance and versioning

Add two independent versions:

### 12.1 Dataset version
Semantic versioning for the repository dataset:
- `MAJOR`: breaking schema or major reprocessing
- `MINOR`: new sensors or improved curves
- `PATCH`: metadata or non-breaking fixes

### 12.2 Source version
Per-source document version:
- e.g. `S2-SRF 4.0`
- e.g. `MCST Terra RSR tables`
- e.g. `NOAA-21 VIIRS RSR modified 2026-01-31`

### 12.3 Change tracking
Maintain a decision log under `docs/decisions/` for:
- why a source was chosen
- why an approximation was accepted or rejected
- why a curve was trimmed or resampled a certain way

---

## 13. Milestones

### Milestone 0 — schema and registry
- finalize source tiers
- create registry tables
- create source manifest template
- add validation plotting utilities

### Milestone 1 — P0 public multispectral backbone
- Landsat
- Sentinel-2 A/B/C
- MODIS Terra/Aqua
- VIIRS SNPP / NOAA-20 / NOAA-21

### Milestone 2 — broaden public science-grade coverage
- Sentinel-3 OLCI
- ASTER
- PACE OCI
- EnMAP

### Milestone 3 — metadata-driven hyperspectral support
- DESIS
- EMIT
- PROBA-V
- ocean-colour legacy sensors via OBPG

### Milestone 4 — partial / approximation-aware support
- PRISMA
- Planet family
- Airbus / regional / vendor-driven sensors

---

## 14. Concrete next actions

1. Freeze the schema and registry fields before downloading more sources.
2. Build the source manifest and parser interface.
3. Ingest **Landsat, Sentinel-2, MODIS, VIIRS** first.
4. Add validation plots to CI.
5. Only then broaden to OLCI / ASTER / hyperspectral missions.

---

## 15. Definition of done for a sensor unit

A sensor unit is complete only when all of the following exist:
- registry entry
- raw source archived with checksum
- parser script
- canonical native curve table
- metadata sidecar
- validation plot
- unit tests
- release note entry

---

## 16. Recommended README headline message

> This repository stores **canonical native-support relative spectral response functions** for satellite sensors, plus **derived common-grid products** for simulation and bandpass convolution. Official mission sources are preferred; alternative or approximate curves are explicitly labeled and versioned.
