# `rsrf` Sensor Definition Handoff

## Purpose

This document defines the `rsrf`-side work needed for `rsrf` to become the
single owner of:

- sensor definition parsing,
- response-function parsing and realization,
- sensor definition validation,
- sensor definition serialization,
- namespaced downstream metadata that travels with sensor definitions.

This is a handoff specification for `rsrf`. It does not define what
`spectral-library` should do internally after `rsrf` exposes this contract.

## Goal

`rsrf` should expose one stable sensor-definition model that works for both:

- canonical sensors from the `rsrf` registry,
- custom sensors supplied by users.

That model must be able to carry downstream package metadata in a namespaced
extension block, so package-specific concepts such as `spectral_library`
segment assignment are validated and preserved by `rsrf` instead of being
handled in ad hoc local JSON formats.

## Ownership Boundary

`rsrf` should own:

- sensor-definition schema,
- sensor-definition load and dump APIs,
- sensor-definition validation,
- response-definition coercion,
- curve realization,
- registry lookup for full sensor definitions,
- extension-schema validation for downstream packages.

This document recommends a namespaced extension model:

- generic SRF concepts stay top-level,
- downstream-specific concepts live under `extensions.<consumer_name>`.

For `spectral-library`, the required namespace is:

- `extensions.spectral_library`

## Required Deliverables

`rsrf` should add all of the following.

### 1. First-Class Sensor Definition Model

`rsrf` should define a stable sensor-definition model with two main objects:

- `SensorDefinition`
- `BandDefinition`

Minimum required fields:

`SensorDefinition`
- `schema_type`
- `schema_version`
- `sensor_id`
- `bands`

`BandDefinition`
- `band_id`
- `response_definition`
- `extensions`

`band_id` must be unique within one sensor definition.

### 2. Namespaced Extension Support

`rsrf` should support a generic `extensions` object on both sensor and band
definitions.

The initial required downstream extension is:

- `extensions.spectral_library.segment`

That field is library-specific metadata, not a universal SRF concept, so it
should not be promoted to a top-level `rsrf` field.

### 3. `spectral_library` Extension Schema

`rsrf` should define and validate a concrete extension schema for
`extensions.spectral_library`.

Minimum required band-level fields:

- `segment`

Allowed values:

- `vnir`
- `swir`

The `spectral_library` extension block should be rejected if:

- `segment` is missing,
- `segment` is not one of the supported enum values,
- unknown fields are present inside the extension block before they are
  versioned and documented.

### 4. Stable Sensor Definition IO

`rsrf` should provide stable round-trip APIs for full sensor definitions.

Minimum API surface:

```python
sensor_definition_to_dict(sensor_definition) -> dict
sensor_definition_from_dict(payload: dict) -> SensorDefinition
load_sensor_definition(source, *, root=None) -> SensorDefinition
dump_sensor_definition(sensor_definition, destination) -> None
```

These APIs must preserve `extensions` content exactly.

### 5. One Coercion Entry Point

`rsrf` should provide one entry point that normalizes all supported sensor
inputs into a validated `SensorDefinition`.

Recommended API:

```python
coerce_sensor_definition(
    sensor_definition_input,
    *,
    representation_variant=None,
    root=None,
) -> SensorDefinition
```

Supported input types should include:

- canonical sensor id from the `rsrf` registry,
- dict payload,
- JSON file path,
- already-constructed `SensorDefinition`.

Callable support is optional. It is not required for this handoff.

### 6. Full-Sensor Registry APIs

`rsrf` registry APIs should return full normalized sensor definitions, not only
band listings or realized curves.

Minimum API surface:

```python
get_sensor_definition(
    sensor_id: str,
    *,
    representation_variant=None,
    root=None,
) -> SensorDefinition

list_sensor_definitions(*, representation_variant=None, root=None) -> list[str]
```

Registry-backed and custom sensor definitions must normalize to the same
output model.

### 7. Whole-Sensor Validation

`rsrf` should validate whole sensor definitions, not only per-band curve
payloads.

Minimum validation rules:

- required top-level fields are present,
- `sensor_id` is non-empty,
- `bands` is non-empty,
- each band has a unique `band_id`,
- each band has a valid `response_definition`,
- realized sampled wavelengths are strictly increasing,
- realized response contains at least one positive sample,
- extension blocks conform to their declared schema.

### 8. Versioned Sensor Definition Schema

`rsrf` should version the serialized sensor-definition contract.

Recommended top-level fields:

- `schema_type = "rsrf_sensor_definition"`
- `schema_version = "1.0.0"`

That version applies to the sensor-definition document itself, not to any
individual response profile type.

## Recommended JSON Shape

```json
{
  "schema_type": "rsrf_sensor_definition",
  "schema_version": "1.0.0",
  "sensor_id": "custom_example_sensor",
  "bands": [
    {
      "band_id": "blue",
      "response_definition": {
        "kind": "gaussian",
        "center_wavelength_nm": 490.0,
        "fwhm_nm": 65.0
      },
      "extensions": {
        "spectral_library": {
          "segment": "vnir"
        }
      }
    },
    {
      "band_id": "swir1",
      "response_definition": {
        "kind": "sampled",
        "wavelength_nm": [1550.0, 1600.0, 1650.0],
        "response": [0.1, 1.0, 0.1]
      },
      "extensions": {
        "spectral_library": {
          "segment": "swir"
        }
      }
    }
  ]
}
```

## Recommended JSON Schema Fragment

This fragment captures the minimum structural contract. `response_definition`
can continue to use `rsrf`'s existing response-profile validation rules.

```json
{
  "$id": "https://example.org/rsrf/schemas/sensor-definition-1.0.0.json",
  "type": "object",
  "required": ["schema_type", "schema_version", "sensor_id", "bands"],
  "properties": {
    "schema_type": {
      "const": "rsrf_sensor_definition"
    },
    "schema_version": {
      "type": "string"
    },
    "sensor_id": {
      "type": "string",
      "minLength": 1
    },
    "bands": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "required": ["band_id", "response_definition"],
        "properties": {
          "band_id": {
            "type": "string",
            "minLength": 1
          },
          "response_definition": {
            "type": "object"
          },
          "extensions": {
            "type": "object",
            "properties": {
              "spectral_library": {
                "type": "object",
                "required": ["segment"],
                "properties": {
                  "segment": {
                    "type": "string",
                    "enum": ["vnir", "swir"]
                  }
                },
                "additionalProperties": false
              }
            },
            "additionalProperties": true
          }
        },
        "additionalProperties": false
      }
    }
  },
  "additionalProperties": false
}
```

## Recommended Python Shape

The exact implementation can vary, but the model should be equivalent to:

```python
from dataclasses import dataclass, field


@dataclass(frozen=True)
class BandDefinition:
    band_id: str
    response_definition: dict
    extensions: dict = field(default_factory=dict)


@dataclass(frozen=True)
class SensorDefinition:
    schema_type: str
    schema_version: str
    sensor_id: str
    bands: tuple[BandDefinition, ...]
```

`rsrf` should validate and normalize inputs before returning these objects.

## Validation Requirements

When `extensions.spectral_library` is present, `rsrf` should enforce:

- `segment` is required,
- `segment` must be `vnir` or `swir`,
- no undocumented fields are allowed inside the `spectral_library` block.

When realizing a curve from `response_definition`, `rsrf` should also enforce:

- sampled wavelengths are strictly increasing,
- wavelength and response arrays have the same length,
- at least one response sample is strictly positive,
- invalid or empty realized support is rejected.

## Compatibility Rules

`rsrf` should treat the sensor-definition schema as a versioned public
contract.

Recommended policy:

- additive fields may be introduced in minor versions,
- field renames, removals, or required-field changes require a major schema
  version change,
- extension-schema changes for `spectral_library` must follow the same rule.

## Minimum Test Coverage

`rsrf` should add tests for:

- canonical sensor id to `SensorDefinition`,
- custom dict payload to `SensorDefinition`,
- custom JSON file to `SensorDefinition`,
- sensor-definition round-trip through dict and JSON,
- preservation of `extensions.spectral_library.segment`,
- rejection of duplicate `band_id`,
- rejection of missing `segment`,
- rejection of invalid `segment`,
- rejection of invalid realized sampled curves.

## Implementation Checklist

1. Add `SensorDefinition` and `BandDefinition`.
2. Add `sensor_definition_from_dict(...)`.
3. Add `sensor_definition_to_dict(...)`.
4. Add `load_sensor_definition(...)`.
5. Add `dump_sensor_definition(...)`.
6. Add `coerce_sensor_definition(...)`.
7. Add `get_sensor_definition(...)`.
8. Add `list_sensor_definitions(...)`.
9. Add validation for `extensions.spectral_library.segment`.
10. Add schema-version handling for serialized sensor definitions.
11. Add round-trip and validation tests.

## Acceptance Criteria

This handoff is complete when `rsrf` can:

- return a full `SensorDefinition` for a registry sensor,
- load the same model from a custom JSON document,
- preserve `extensions.spectral_library.segment` through round-trip
  serialization,
- reject invalid `spectral_library` extension payloads,
- expose one stable API path for both canonical and custom sensors.
