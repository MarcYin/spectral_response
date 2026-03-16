# Relative Spectral Response Function (RSRF) repository plan v3

## 1. Goal

Build a reproducible, versioned repository and Python package that provides source-native spectral response definitions for spaceborne optical sensors. The repository must support both full sampled spectral response curves and official band specifications that only provide center wavelengths, FWHM values, band indices, or a wavelength grid.

Supported downstream uses:
- spectral simulation
- bandpass convolution
- sensor harmonization / cross-walking
- QA and reproducible ingest pipelines
- metadata-driven hyperspectral support where only wavelength-grid and FWHM metadata are available

This revision keeps the strengths of v2 but removes a major limitation: the canonical source of truth is not always a sampled curve. For many hyperspectral sensors, the canonical source is a band specification table.

Status note:
- This is the baseline architecture document.
- `rsrf_repo_plan_v2.md` is retained for history only.
- The implementation sequence and first backlog now live in `rsrf_implementation_plan.md`.

---

## 2. Scope and non-goals

### 2.1 In-scope for v1

Spaceborne sensors with bands in at least one of:
- UV / VIS / NIR / SWIR
- TIR, if an official or high-quality alternative SRF exists

### 2.2 Priority families

#### P0 - highest value, strong public sources
- Landsat MSS / TM / ETM+ / OLI / TIRS
- Sentinel-2 MSI: S2A, S2B, S2C
- MODIS: Terra, Aqua
- VIIRS: SNPP, NOAA-20, NOAA-21
- Sentinel-3 OLCI: S3A, S3B
- ASTER

#### P1 - strong scientific value, some metadata-driven handling
- PACE OCI
- EnMAP
- DESIS
- EMIT
- PROBA-V
- ocean-colour legacy sensors via NASA OBPG curated tables

#### P2 - partial / gated / vendor-doc driven
- PRISMA
- PlanetScope: PS2, PS2.SD, PSB.SD
- RapidEye
- SkySat
- Pleiades / Pleiades Neo / SPOT families
- Satellogic NewSat
- Amazonia-1, CBERS-4A, Formosat-5, and similar regional missions

### 2.3 Explicit non-goals for v1
- deriving physics-grade SRFs from brochure band centers with weak provenance
- mixing approximate curves with official sampled curves without clear labeling
- forcing every canonical representation into a dense 300-2500 nm curve table
- requiring precomputed dense curves for hyperspectral sensors when on-demand realization is more appropriate

---

## 3. Core design decision

## Canonical storage must preserve the source-native response definition.

The source-native response definition may be one of:
1. `sampled_curve` - source provides wavelength / response pairs
2. `band_spec` - source provides per-band center wavelength, FWHM, band index, optional shape metadata, or wavelength grid only
3. `hybrid` - source provides both sampled curves and a band-spec summary

Why:
- many sensors have thermal bands beyond 2500 nm
- some sources provide detector-, camera-, scene-, or pixel-dependent responses
- many hyperspectral sensors publish band centers and FWHM arrays but not full SRF curves
- dense common grids are useful, but they are derived products, not the scientific source of truth

### 3.1 Recommended three-layer design

#### Layer A - canonical source definition (`canonical`)
Store the source-native response definition exactly as published.

Canonical subtypes:
- `sampled_curve`: native wavelength axis plus relative response values
- `band_spec`: per-band metadata such as center wavelength, FWHM, band index, band status, optional shape type, optional parameter values

#### Layer B - optional realized curve (`realized`)
Create a sampled curve only when needed.

Use cases:
- build convolution weights on a user spectrum grid
- create visualizations
- materialize an approximate or official parametric profile into sampled points
- cache results for repeated use

Realized curves can be:
- `official_parametric` when the source explicitly defines the shape
- `approximate_parametric` when shape must be assumed, e.g. Gaussian from center plus FWHM

#### Layer C - derived common grid (`common_grid`)
Generate convenience products on fixed grids, for example:
- `reflective_300_2500_1nm`
- `reflective_300_2500_0p1nm`
- `tir_2500_14000_1nm`
- optional combined `vswir_tir_380_14000_1nm`

For metadata-only hyperspectral sensors, this layer should be optional. Often it is better to compute weights directly on the target spectrum grid than to store very large dense grids for every band.

### 3.2 Canonical normalization policy

Store sampled curves as relative response in [0, 1], preserving the published shape. Do not force area-normalization in storage.

Use runtime normalization for convolution:

```text
L_band = sum(L_i * R_i * d_lambda_i) / sum(R_i * d_lambda_i)
```

For `band_spec` entries, store published center/FWHM values without inventing a sampled curve.

### 3.3 Band-spec and realization policy

If the source only provides wavelength-grid and FWHM information:
- the official published band table is canonical `band_spec`
- the canonical entry is not itself an approximation
- any realized sampled curve must declare its profile model and provenance
- if the shape is not published, the realized curve is an approximation
- the approximation flag belongs to the realized representation, not to the canonical band specification

If the source publishes a parametric shape model, e.g. Gaussian, top-hat, super-Gaussian, triangular, asymmetric Gaussian, or another explicit formula:
- store the published parameters in canonical `band_spec`
- realized curves produced from that published model are not approximations

### 3.4 Default realization rule for FWHM-only sensors

When a user asks for a sampled curve from a `band_spec` that includes only center wavelength and FWHM:
- default profile: `gaussian`
- sigma conversion: `sigma = fwhm / (2 * sqrt(2 * ln(2)))`
- default support rule: `center +/- 4 sigma`
- default sampling rule for local realization: `step_nm = min(fwhm_nm / 10, 1.0)` with a lower bound set by numerical stability policy
- record all realization parameters in metadata

These defaults are for a derived representation only and must never overwrite the canonical source definition.

---

## 4. Source quality tiers

Every source artifact must have a `source_tier`.

### Tier A - official downloadable sampled SRF/RSR
Examples:
- official Excel / CSV / text tables
- official mission web pages with downloadable sampled SRF data

### Tier B - official machine-readable spectral metadata or parametric band specification
Examples:
- per-product or per-mission metadata containing wavelength-grid and FWHM arrays
- official XLSX / CSV / JSON with band centers, FWHM, band status, or parametric shape metadata
- official PDF / XLSX with extractable curves or structured band specifications

### Tier C - official landing page or narrative documentation only
Examples:
- official docs expose band centers/FWHM only in a brochure or web table with no machine-readable artifact and weak extractability

### Tier D - trusted alternative curated source
Examples:
- NASA OBPG curated SRF tables
- NWP SAF SRF catalogue
- USGS Spectral Characteristics Viewer

### Tier E - documented approximation
Examples:
- Gaussian reconstructed from official center wavelength + FWHM with no official shape model
- literature-derived reconstruction when no official full curve is public

### Policy
- `A`, `B`, and `D` can be published in the main dataset
- `C` stays in the registry but is not ingest-complete unless it is converted into a reviewed extracted table with a committed parser and strong provenance notes
- `E` can be published only if explicitly labeled `approximation=true` and kept separate from official canonical representations

---

## 5. Sensor identity and representation model

The registry remains sensor-unit-centric.

Use three levels:
1. `mission_family` - e.g. `sentinel-2`
2. `sensor_unit` - e.g. `sentinel-2c_msi`
3. `representation_variant` - e.g. `band_average`, `camera_column`, `metadata_band_spec`, `official_parametric`, `gaussian_from_fwhm`

Recommended additional representation fields:
- `content_kind`: `sampled_curve`, `band_spec`, or `hybrid`
- `realization_kind`: `none`, `official_parametric`, `approximate_parametric`
- `spectral_calibration_scope`: `mission_average`, `sensor_unit`, `camera`, `detector`, `scene_product`, `pixel`

### Example IDs
- `landsat-9_oli-2.band-average.B05`
- `sentinel-2c_msi.band-average.B08`
- `sentinel-3b_olci.camera-column.Oa08`
- `viirs_noaa21.product-order.M05`
- `desis_iss.metadata-band-spec.B123`
- `desis_iss.gaussian-from-fwhm.B123`

This preserves distinctions such as:
- S2A vs S2B vs S2C
- SNPP vs NOAA-20 vs NOAA-21 VIIRS
- OLCI-A vs OLCI-B
- detector-order vs product-order variants
- official band specifications vs realized approximate curves

---

## 6. Recommended repository structure

```text
repo/
  README.md
  pyproject.toml
  src/rsrf/
    registry.py
    io.py
    band_specs.py
    realize.py
    resample.py
    convolve.py
    validate.py
    plotting.py
  data/
    registry/
      sensors.parquet
      bands.parquet
      sources.parquet
      band_specs.parquet
      realizations.parquet
    canonical/
      sampled_curve/<sensor_unit>/<representation_variant>/curves.parquet
      sampled_curve/<sensor_unit>/<representation_variant>/metadata.json
      band_spec/<sensor_unit>/<representation_variant>/band_specs.parquet
      band_spec/<sensor_unit>/<representation_variant>/metadata.json
    realized/
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
- `parquet` remains efficient for long-form tables and metadata
- canonical `band_spec` is now first-class instead of being forced into `curves.parquet`
- `realized/` separates generated curves from source-truth artifacts
- hyperspectral sensors can be supported without precomputing dense curves for every band

---

## 7. Data model

### 7.1 Registry tables

### `sensors.parquet`
One row per sensor unit / representation variant.

Suggested fields:
- `sensor_unit_id`
- `mission_family`
- `platform`
- `instrument`
- `representation_variant`
- `content_kind` (`sampled_curve`, `band_spec`, `hybrid`)
- `realization_kind` (`none`, `official_parametric`, `approximate_parametric`)
- `spectral_calibration_scope`
- `spectral_domain`
- `source_tier`
- `approximation`
- `official_source_available`
- `band_count`
- `license_note`
- `status` (`planned`, `registered`, `ingested`, `validated`, `released`)

### `bands.parquet`
One row per band.

Suggested fields:
- `sensor_unit_id`
- `representation_variant`
- `band_id`
- `band_index`
- `band_name`
- `center_wavelength_nm`
- `fwhm_nm`
- `published_shape_type` (`sampled`, `gaussian`, `super_gaussian`, `top_hat`, `triangular`, `asymmetric_gaussian`, `unknown`)
- `band_status` (`nominal`, `recommended`, `masked`, `excluded`, `diagnostic`)
- `native_support_min_nm` (nullable)
- `native_support_max_nm` (nullable)
- `native_sampling_nm` (nullable)
- `normalization`
- `has_sampled_curve`
- `has_band_spec`

### `sources.parquet`
One row per source artifact.

Suggested fields:
- `source_id`
- `sensor_unit_id`
- `representation_variant`
- `source_tier`
- `source_type` (`official`, `official_metadata`, `alternative`, `literature`)
- `content_kind`
- `title`
- `url`
- `retrieved_at`
- `file_sha256`
- `doc_version`
- `notes`

### `band_specs.parquet`
One row per canonical band specification.

Suggested fields:
- `sensor_unit_id`
- `representation_variant`
- `band_id`
- `band_index`
- `center_wavelength_nm`
- `fwhm_nm`
- `published_shape_type`
- `shape_param_json`
- `band_status`
- `is_official`
- `source_id`

Use this table when the source-native truth is a band specification rather than a sampled response curve.

### `realizations.parquet`
One row per realized-curve recipe.

Suggested fields:
- `realization_id`
- `sensor_unit_id`
- `source_representation_variant`
- `output_representation_variant`
- `profile_type`
- `profile_param_json`
- `grid_policy`
- `support_rule`
- `normalization`
- `approximation`
- `approximation_reason`
- `source_id`

This table records how a sampled curve was generated from a canonical `band_spec`.

### 7.2 Curve storage (`curves.parquet`)

Use a long-form table:
- `sensor_unit_id`
- `representation_variant`
- `band_id`
- `wavelength_nm`
- `response`
- `curve_origin` (`canonical_sampled`, `realized_parametric`, `common_grid`)
- `realization_id` (nullable)
- `is_native`
- `is_trimmed`
- `source_id`

This keeps sampled data queryable in pandas / polars / DuckDB while preserving how the curve was obtained.

---

## 8. Normalization, trimming, zero, and approximation policy

### 8.1 Published axis first
Do not invent a new wavelength axis for canonical storage if the source already provides one.

### 8.2 Band-spec first
Do not invent a sampled curve for canonical storage when the source only provides center/FWHM metadata.

### 8.3 Trimming
For canonical sampled curves:
- preserve source support when available
- optionally store a trimmed copy with `epsilon_zero_threshold`
- record the trimming rule in metadata

For realized curves from `band_spec`:
- trimming is part of the realization recipe, not a property of the canonical source

### 8.4 Zero policy
- clip tiny negative numeric artifacts to zero
- record the threshold used
- preserve interior zeros
- do not smooth source curves unless a separate derived representation is created

### 8.5 Approximation policy
If only center wavelength and FWHM exist and the source does not define the band shape:
- canonical representation: `metadata_band_spec`
- derived representation: `gaussian_from_fwhm` or another explicit model
- require `approximation=true` on the realized representation
- require `approximation_reason`
- never silently merge approximations with official sampled curves

### 8.6 Hyperspectral policy
For sensors with tens to hundreds of bands:
- support `band_index` as a first-class identifier
- allow unnamed or machine-generated `band_id` values such as `B001`, `B002`, ...
- allow optional `band_status` fields for masked or excluded channels
- prefer on-demand realization over precomputing dense common-grid files for all bands

---

## 9. Validation pipeline

A sensor is not done when the file is downloaded. It is done when it passes QA appropriate to its canonical form.

### 9.1 Automated checks for sampled curves
- wavelengths strictly increasing within each band
- no duplicate `(band_id, wavelength_nm)` pairs
- response values finite and >= 0
- maximum response > 0
- support range recorded and consistent
- expected band count matches source
- checksum present for raw source file

### 9.2 Automated checks for band specifications
- `band_index` unique within each representation
- center wavelengths finite and strictly increasing unless the source explicitly defines a different order
- FWHM finite and > 0 for bands where it is provided
- expected band count matches source
- band status values valid
- checksum present for raw source file

### 9.3 Scientific QA
- overlay plots against source figure or alternative trusted source where possible
- compare center and FWHM derived from ingested sampled curves vs documented values
- if a realized curve is generated from `band_spec`, verify recovered center and FWHM against the source values within tolerance
- compare common-grid resampling integrals vs native or realized-curve integrals where relevant
- flag suspicious multi-peak or truncated shapes

### 9.4 Release gates
Minimum release criteria for a sensor unit:
- raw source archived
- parser script committed
- metadata complete
- automated tests passing
- source tier assigned
- either canonical sampled curves exist or canonical band specifications exist
- if a realized approximation is published, the realization recipe and approximation label must be present

---

## 10. Package API suggestions

The repository should power a small but stable Python API that is not curve-only.

### 10.1 Read API
- `list_sensors()`
- `list_bands(sensor_unit_id, representation_variant=None)`
- `get_metadata(sensor_unit_id, representation_variant=None)`
- `load_response_definition(sensor_unit_id, band_id, representation_variant=None)`
- `load_curve(sensor_unit_id, band_id, variant="canonical")`
- `load_band_spec(sensor_unit_id, band_id, variant="metadata_band_spec")`

### 10.2 Processing API
- `realize_curve(band_spec, profile=None, grid_spec="adaptive")`
- `resample_curve(curve, grid_nm)`
- `build_common_grid(sensor_unit_id, grid_spec, source_variant=None)`
- `convolution_weights(response_def, spectrum_grid_nm)`
- `convolve_spectrum(spectrum, response_def)`
- `effective_wavelength(response_def, weighting="flat")`

`response_def` should accept either a sampled curve or a band specification. The library should realize a curve lazily when needed.

### 10.3 Discovery API
- `find_equivalent_bands(sensor_a, sensor_b)`
- `registry_search(mission=None, domain=None, source_tier=None, content_kind=None)`

---

## 11. Recommended initial source map

### P0 ingest now
- USGS Spectral Characteristics Viewer for Landsat family and additional bootstrap sensors
- Copernicus / SentiWiki for Sentinel-2 SRF files, including S2C
- MCST for MODIS Terra/Aqua RSR tables
- NOAA NCC for VIIRS SNPP / NOAA-20 / NOAA-21 RSRs
- official Sentinel-3 docs for OLCI and SLSTR
- ASTER JPL mission pages for VNIR / SWIR / TIR response data

### P1 ingest after schema is stable
- NASA OBPG SRF tables for ocean-colour and curated cross-checks
- PACE OCI characterization pages
- EnMAP spectral bands update workbooks and metadata tables
- DESIS metadata / STAC / workshop notes
- EMIT spectral properties pages
- PROBA-V docs

### P2 registry-first, ingest later
- PRISMA official portal and acquisition catalogue
- Planet docs for PlanetScope / RapidEye / SkySat
- Airbus resource-center docs for Pleiades / SPOT families
- vendor / regional missions with only landing pages or partial specs

---

## 12. Governance and versioning

Maintain two independent versions.

### 12.1 Dataset version
Semantic versioning for the dataset:
- `MAJOR`: breaking schema or major reprocessing
- `MINOR`: new sensors, new canonical forms, or improved curves
- `PATCH`: metadata or non-breaking fixes

### 12.2 Source version
Per-source document version, for example:
- `S2-SRF 4.0`
- `MCST Terra RSR tables`
- `NOAA-21 VIIRS RSR modified 2026-01-31`

### 12.3 Change tracking
Maintain a decision log under `docs/decisions/` for:
- why a source was chosen
- why a canonical form is `sampled_curve` vs `band_spec`
- why an approximation was accepted or rejected
- why a realization recipe, trimming rule, or resampling rule was used

---

## 13. Milestones

### Milestone 0 - repository bootstrap and schema freeze
- initialize the Python package, CLI entrypoint, test suite, and directory layout
- finalize source tiers and the canonical `sampled_curve` / `band_spec` split
- add `content_kind`, `band_specs`, and `realizations` schema support
- create the manifest validator and parser interface
- add validation plotting utilities

### Milestone 1 - reference vertical slices
- ingest one official sampled-curve source end to end: Sentinel-2C MSI
- ingest one metadata-only band-spec source end to end: hyperspectral band-spec example
- verify both canonical forms can be listed, loaded, validated, and plotted through one API

### Milestone 2 - P0 public multispectral backbone
- Landsat family
- Sentinel-2 A/B
- MODIS Terra/Aqua
- VIIRS SNPP / NOAA-20 / NOAA-21

### Milestone 3 - broaden public science-grade coverage
- Sentinel-3 OLCI
- ASTER
- PACE OCI
- EnMAP

### Milestone 4 - metadata-driven hyperspectral expansion
- DESIS
- EMIT
- PROBA-V
- ocean-colour legacy sensors via OBPG
- on-demand curve realization from official wavelength-grid + FWHM tables

### Milestone 5 - partial / approximation-aware support
- PRISMA
- Planet family
- Airbus / regional / vendor-driven sensors

---

## 14. Concrete next actions

1. Create the repository skeleton before adding more source files:
   - `pyproject.toml`
   - `src/rsrf/`
   - `scripts/ingest/`
   - `tests/`
   - `docs/`
2. Freeze the manifest and registry schema with first-class `band_spec` support.
3. Implement the parser contract so a source can emit `curves.parquet`, `band_specs.parquet`, or both.
4. Implement shared read/write helpers for registry tables, canonical outputs, and metadata sidecars.
5. Implement validation and plotting utilities before bulk ingest.
6. Prove the stack with two reference ingests only:
   - sampled curve: Sentinel-2C MSI
   - band spec: hyperspectral band-spec example
7. Add lazy realization utilities for `gaussian_from_fwhm` and future official parametric models.
8. Only after the two reference ingests pass QA should the project expand to Landsat, MODIS, VIIRS, and the wider P0 set.

---

## 15. Definition of done for a sensor unit

A sensor unit is complete only when all of the following exist:
- registry entry
- raw source archived with checksum
- parser script
- canonical sampled curve table or canonical band specification table
- metadata sidecar
- validation output appropriate to the canonical form
- unit tests
- release note entry

If an approximate realized curve is also released, it additionally requires:
- a committed realization recipe
- `approximation=true`
- an explicit approximation reason

---

## 16. Recommended README headline message

> This repository stores canonical source-native spectral response definitions for satellite sensors, including both sampled spectral response curves and official band-specification metadata. Derived common-grid products and realized approximate curves are generated separately, fully labeled, and versioned.

---

## 17. Implementation stance

The main revision to the earlier planning is sequencing:

- Do not start by onboarding many sensors in parallel.
- First build one complete sampled-curve pipeline and one complete band-spec pipeline.
- Treat `common_grid` products as a downstream build target, not as a blocker for the first implementation pass.
- Freeze the parser contract and validation rules before scaling source coverage.
