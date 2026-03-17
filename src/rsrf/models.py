"""Core enums and typed models for the repository bootstrap."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Mapping, Optional, Sequence


class ManifestValidationError(ValueError):
    """Raised when a manifest cannot be parsed into the typed model."""

    def __init__(self, errors: Sequence[str]) -> None:
        self.errors = list(errors)
        super().__init__("manifest validation failed")


class ContentKind(str, Enum):
    """Supported canonical content kinds."""

    SAMPLED_CURVE = "sampled_curve"
    BAND_SPEC = "band_spec"
    HYBRID = "hybrid"


class SourceTier(str, Enum):
    """Source quality tier."""

    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"


class SourceType(str, Enum):
    """Supported source provenance categories."""

    OFFICIAL = "official"
    OFFICIAL_METADATA = "official_metadata"
    ALTERNATIVE = "alternative"
    LITERATURE = "literature"


@dataclass(frozen=True)
class BandSpec:
    """Metadata-only band specification."""

    band_id: str
    center_wavelength_nm: float
    fwhm_nm: float
    band_index: Optional[int] = None
    band_name: Optional[str] = None
    band_status: str = "nominal"
    published_shape_type: str = "unknown"
    shape_param_json: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SampledCurve:
    """Sampled response curve."""

    band_id: str
    wavelength_nm: Sequence[float]
    response: Sequence[float]
    source_variant: Optional[str] = None


@dataclass(frozen=True)
class ManifestSummary:
    """Small manifest summary used by the CLI and ingest scripts."""

    source_id: str
    sensor_unit_id: str
    representation_variant: str
    content_kind: str
    source_tier: str

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "ManifestSummary":
        return cls(
            source_id=str(payload.get("source_id", "")),
            sensor_unit_id=str(payload.get("sensor_unit_id", "")),
            representation_variant=str(payload.get("representation_variant", "")),
            content_kind=str(payload.get("content_kind", "")),
            source_tier=str(payload.get("source_tier", "")),
        )

    @classmethod
    def from_manifest(cls, manifest: "SourceManifest") -> "ManifestSummary":
        return cls(
            source_id=manifest.source_id,
            sensor_unit_id=manifest.sensor_unit_id,
            representation_variant=manifest.representation_variant,
            content_kind=manifest.content_kind.value,
            source_tier=manifest.source_tier.value,
        )


@dataclass(frozen=True)
class ParserOutputs:
    """Declared outputs emitted by a parser."""

    canonical: tuple[str, ...]
    optional: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any], *, prefix: str = "parser.outputs") -> "ParserOutputs":
        errors: list[str] = []
        canonical = _required_string_list(payload, "canonical", errors, prefix)
        optional = _optional_string_list(payload, "optional", errors, prefix)
        if not canonical:
            errors.append(f"{prefix}.canonical must contain at least one output")
        if errors:
            raise ManifestValidationError(errors)
        return cls(canonical=tuple(canonical), optional=tuple(optional))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "canonical": list(self.canonical),
            "optional": list(self.optional),
        }


@dataclass(frozen=True)
class ParserSpec:
    """Parser declaration section."""

    script: str
    entrypoint: str
    outputs: ParserOutputs
    notes: tuple[str, ...]

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any], *, prefix: str = "parser") -> "ParserSpec":
        errors: list[str] = []
        script = _required_string(payload, "script", errors, prefix)
        entrypoint = _required_string(payload, "entrypoint", errors, prefix)
        outputs_payload = _required_mapping(payload, "outputs", errors, prefix)
        notes = _required_string_list(payload, "notes", errors, prefix)
        if errors:
            raise ManifestValidationError(errors)

        try:
            outputs = ParserOutputs.from_dict(outputs_payload, prefix=f"{prefix}.outputs")
        except ManifestValidationError as exc:
            errors.extend(exc.errors)
            raise ManifestValidationError(errors)

        return cls(
            script=script,
            entrypoint=entrypoint,
            outputs=outputs,
            notes=tuple(notes),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "script": self.script,
            "entrypoint": self.entrypoint,
            "outputs": self.outputs.to_dict(),
            "notes": list(self.notes),
        }


@dataclass(frozen=True)
class CanonicalSpec:
    """Canonical source definition metadata."""

    kind: ContentKind
    spectral_calibration_scope: str
    axis_policy: str
    normalization: str
    published_shape_type: str

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any], *, prefix: str = "canonical") -> "CanonicalSpec":
        errors: list[str] = []
        kind_raw = _required_string(payload, "kind", errors, prefix)
        spectral_calibration_scope = _required_string(
            payload, "spectral_calibration_scope", errors, prefix
        )
        axis_policy = _required_string(payload, "axis_policy", errors, prefix)
        normalization = _required_string(payload, "normalization", errors, prefix)
        published_shape_type = _required_string(
            payload, "published_shape_type", errors, prefix
        )
        kind = _enum_from_string(ContentKind, kind_raw, errors, f"{prefix}.kind")
        if errors:
            raise ManifestValidationError(errors)
        return cls(
            kind=kind,
            spectral_calibration_scope=spectral_calibration_scope,
            axis_policy=axis_policy,
            normalization=normalization,
            published_shape_type=published_shape_type,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": self.kind.value,
            "spectral_calibration_scope": self.spectral_calibration_scope,
            "axis_policy": self.axis_policy,
            "normalization": self.normalization,
            "published_shape_type": self.published_shape_type,
        }


@dataclass(frozen=True)
class BandSpecSection:
    """Manifest section describing how to extract band-spec fields."""

    enabled: bool
    band_index_field: Optional[str]
    band_id_field: Optional[str]
    center_wavelength_field: Optional[str]
    fwhm_field: Optional[str]
    band_status_field: Optional[str]
    shape_param_fields: Mapping[str, str]

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any], *, prefix: str = "band_spec") -> "BandSpecSection":
        errors: list[str] = []
        enabled = _required_bool(payload, "enabled", errors, prefix)
        band_index_field = _optional_string(payload, "band_index_field", errors, prefix)
        band_id_field = _optional_string(payload, "band_id_field", errors, prefix)
        center_wavelength_field = _optional_string(
            payload, "center_wavelength_field", errors, prefix
        )
        fwhm_field = _optional_string(payload, "fwhm_field", errors, prefix)
        band_status_field = _optional_string(payload, "band_status_field", errors, prefix)
        shape_param_fields = _optional_string_mapping(
            payload, "shape_param_fields", errors, prefix
        )
        if errors:
            raise ManifestValidationError(errors)
        return cls(
            enabled=enabled,
            band_index_field=band_index_field,
            band_id_field=band_id_field,
            center_wavelength_field=center_wavelength_field,
            fwhm_field=fwhm_field,
            band_status_field=band_status_field,
            shape_param_fields=shape_param_fields,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "band_index_field": self.band_index_field,
            "band_id_field": self.band_id_field,
            "center_wavelength_field": self.center_wavelength_field,
            "fwhm_field": self.fwhm_field,
            "band_status_field": self.band_status_field,
            "shape_param_fields": dict(self.shape_param_fields),
        }


@dataclass(frozen=True)
class GridPolicy:
    """Curve realization grid policy."""

    kind: str
    samples_per_fwhm: int
    max_step_nm: float
    truncate_sigma: float

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any], *, prefix: str = "curve_realization.grid_policy") -> "GridPolicy":
        errors: list[str] = []
        kind = _required_string(payload, "kind", errors, prefix)
        samples_per_fwhm = _required_int(payload, "samples_per_fwhm", errors, prefix)
        max_step_nm = _required_float(payload, "max_step_nm", errors, prefix)
        truncate_sigma = _required_float(payload, "truncate_sigma", errors, prefix)
        if samples_per_fwhm <= 0:
            errors.append(f"{prefix}.samples_per_fwhm must be positive")
        if max_step_nm <= 0:
            errors.append(f"{prefix}.max_step_nm must be positive")
        if truncate_sigma <= 0:
            errors.append(f"{prefix}.truncate_sigma must be positive")
        if errors:
            raise ManifestValidationError(errors)
        return cls(
            kind=kind,
            samples_per_fwhm=samples_per_fwhm,
            max_step_nm=max_step_nm,
            truncate_sigma=truncate_sigma,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": self.kind,
            "samples_per_fwhm": self.samples_per_fwhm,
            "max_step_nm": self.max_step_nm,
            "truncate_sigma": self.truncate_sigma,
        }


@dataclass(frozen=True)
class CurveRealizationSpec:
    """Optional derived sampled-curve realization section."""

    enabled: bool
    output_representation_variant: Optional[str]
    profile_type: Optional[str]
    approximation: bool
    approximation_reason: Optional[str]
    persist_realized_curves: bool
    grid_policy: Optional[GridPolicy]
    normalization: Optional[str]

    @classmethod
    def from_dict(
        cls,
        payload: Mapping[str, Any],
        *,
        prefix: str = "curve_realization",
    ) -> "CurveRealizationSpec":
        errors: list[str] = []
        enabled = _required_bool(payload, "enabled", errors, prefix)
        output_representation_variant = _optional_string(
            payload, "output_representation_variant", errors, prefix
        )
        profile_type = _optional_string(payload, "profile_type", errors, prefix)
        approximation = _required_bool(payload, "approximation", errors, prefix)
        approximation_reason = _optional_string(
            payload, "approximation_reason", errors, prefix
        )
        persist_realized_curves = _required_bool(
            payload, "persist_realized_curves", errors, prefix
        )
        normalization = _optional_string(payload, "normalization", errors, prefix)
        grid_policy_payload = payload.get("grid_policy")

        grid_policy: Optional[GridPolicy] = None
        if grid_policy_payload is not None:
            if not isinstance(grid_policy_payload, Mapping):
                errors.append(f"{prefix}.grid_policy must be an object or null")
            else:
                try:
                    grid_policy = GridPolicy.from_dict(
                        grid_policy_payload,
                        prefix=f"{prefix}.grid_policy",
                    )
                except ManifestValidationError as exc:
                    errors.extend(exc.errors)

        if enabled:
            if not output_representation_variant:
                errors.append(f"{prefix}.output_representation_variant is required when enabled")
            if not profile_type:
                errors.append(f"{prefix}.profile_type is required when enabled")
            if approximation and not approximation_reason:
                errors.append(f"{prefix}.approximation_reason is required when approximation=true")
            if not normalization:
                errors.append(f"{prefix}.normalization is required when enabled")
            if grid_policy is None:
                errors.append(f"{prefix}.grid_policy is required when enabled")

        if errors:
            raise ManifestValidationError(errors)

        return cls(
            enabled=enabled,
            output_representation_variant=output_representation_variant,
            profile_type=profile_type,
            approximation=approximation,
            approximation_reason=approximation_reason,
            persist_realized_curves=persist_realized_curves,
            grid_policy=grid_policy,
            normalization=normalization,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "output_representation_variant": self.output_representation_variant,
            "profile_type": self.profile_type,
            "approximation": self.approximation,
            "approximation_reason": self.approximation_reason,
            "persist_realized_curves": self.persist_realized_curves,
            "grid_policy": None if self.grid_policy is None else self.grid_policy.to_dict(),
            "normalization": self.normalization,
        }


@dataclass(frozen=True)
class ValidationSpec:
    """Release and QA expectations for a source ingest."""

    expected_band_count: int | str
    expected_domain: str
    require_band_spec: bool
    require_sampled_curve: bool
    compare_center_and_fwhm: bool
    plot_overlay_required: bool
    curve_checks_if_realized: bool
    monotonic_centers_required: bool

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any], *, prefix: str = "validation") -> "ValidationSpec":
        errors: list[str] = []
        expected_band_count = _required_int_or_placeholder(
            payload, "expected_band_count", errors, prefix
        )
        expected_domain = _required_string(payload, "expected_domain", errors, prefix)
        require_band_spec = _required_bool(payload, "require_band_spec", errors, prefix)
        require_sampled_curve = _required_bool(payload, "require_sampled_curve", errors, prefix)
        compare_center_and_fwhm = _required_bool(
            payload, "compare_center_and_fwhm", errors, prefix
        )
        plot_overlay_required = _required_bool(
            payload, "plot_overlay_required", errors, prefix
        )
        curve_checks_if_realized = _required_bool(
            payload, "curve_checks_if_realized", errors, prefix
        )
        monotonic_centers_required = _required_bool(
            payload, "monotonic_centers_required", errors, prefix
        )
        if errors:
            raise ManifestValidationError(errors)
        return cls(
            expected_band_count=expected_band_count,
            expected_domain=expected_domain,
            require_band_spec=require_band_spec,
            require_sampled_curve=require_sampled_curve,
            compare_center_and_fwhm=compare_center_and_fwhm,
            plot_overlay_required=plot_overlay_required,
            curve_checks_if_realized=curve_checks_if_realized,
            monotonic_centers_required=monotonic_centers_required,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "expected_band_count": self.expected_band_count,
            "expected_domain": self.expected_domain,
            "require_band_spec": self.require_band_spec,
            "require_sampled_curve": self.require_sampled_curve,
            "compare_center_and_fwhm": self.compare_center_and_fwhm,
            "plot_overlay_required": self.plot_overlay_required,
            "curve_checks_if_realized": self.curve_checks_if_realized,
            "monotonic_centers_required": self.monotonic_centers_required,
        }


@dataclass(frozen=True)
class SourceManifest:
    """Typed source manifest."""

    source_id: str
    sensor_unit_id: str
    representation_variant: str
    source_tier: SourceTier
    source_type: SourceType
    content_kind: ContentKind
    mission_family: str | None
    platform: str | None
    instrument: str | None
    approximation: bool
    approximation_reason: str | None
    title: str
    url: str
    retrieved_at: str
    doc_version: str
    raw_local_path: str
    file_sha256: str
    license_note: str
    parser: ParserSpec
    canonical: CanonicalSpec
    band_spec: BandSpecSection
    curve_realization: CurveRealizationSpec
    validation: ValidationSpec
    notes: tuple[str, ...]

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SourceManifest":
        errors: list[str] = []
        source_id = _required_string(payload, "source_id", errors)
        sensor_unit_id = _required_string(payload, "sensor_unit_id", errors)
        representation_variant = _required_string(payload, "representation_variant", errors)
        source_tier = _enum_from_string(
            SourceTier,
            _required_string(payload, "source_tier", errors),
            errors,
            "source_tier",
        )
        source_type = _enum_from_string(
            SourceType,
            _required_string(payload, "source_type", errors),
            errors,
            "source_type",
        )
        content_kind = _enum_from_string(
            ContentKind,
            _required_string(payload, "content_kind", errors),
            errors,
            "content_kind",
        )
        mission_family = _optional_string(payload, "mission_family", errors)
        platform = _optional_string(payload, "platform", errors)
        instrument = _optional_string(payload, "instrument", errors)
        approximation = payload.get("approximation", False)
        if not isinstance(approximation, bool):
            errors.append("approximation must be a boolean when provided")
            approximation = False
        approximation_reason = _optional_string(payload, "approximation_reason", errors)
        title = _required_string(payload, "title", errors)
        url = _required_string(payload, "url", errors)
        retrieved_at = _required_string(payload, "retrieved_at", errors)
        doc_version = _required_string(payload, "doc_version", errors)
        raw_local_path = _required_string(payload, "raw_local_path", errors)
        file_sha256 = _required_string(payload, "file_sha256", errors)
        license_note = _required_string(payload, "license_note", errors)
        parser_payload = _required_mapping(payload, "parser", errors)
        canonical_payload = _required_mapping(payload, "canonical", errors)
        band_spec_payload = _required_mapping(payload, "band_spec", errors)
        curve_realization_payload = _required_mapping(payload, "curve_realization", errors)
        validation_payload = _required_mapping(payload, "validation", errors)
        notes = _required_string_list(payload, "notes", errors)
        if errors:
            raise ManifestValidationError(errors)

        try:
            parser = ParserSpec.from_dict(parser_payload)
        except ManifestValidationError as exc:
            errors.extend(exc.errors)
            parser = None  # type: ignore[assignment]
        try:
            canonical = CanonicalSpec.from_dict(canonical_payload)
        except ManifestValidationError as exc:
            errors.extend(exc.errors)
            canonical = None  # type: ignore[assignment]
        try:
            band_spec = BandSpecSection.from_dict(band_spec_payload)
        except ManifestValidationError as exc:
            errors.extend(exc.errors)
            band_spec = None  # type: ignore[assignment]
        try:
            curve_realization = CurveRealizationSpec.from_dict(curve_realization_payload)
        except ManifestValidationError as exc:
            errors.extend(exc.errors)
            curve_realization = None  # type: ignore[assignment]
        try:
            validation = ValidationSpec.from_dict(validation_payload)
        except ManifestValidationError as exc:
            errors.extend(exc.errors)
            validation = None  # type: ignore[assignment]

        if errors:
            raise ManifestValidationError(errors)

        if content_kind == ContentKind.SAMPLED_CURVE and canonical.kind != ContentKind.SAMPLED_CURVE:
            errors.append("canonical.kind must be sampled_curve when content_kind=sampled_curve")
        if content_kind == ContentKind.BAND_SPEC and canonical.kind != ContentKind.BAND_SPEC:
            errors.append("canonical.kind must be band_spec when content_kind=band_spec")
        if content_kind == ContentKind.BAND_SPEC and not band_spec.enabled:
            errors.append("band_spec.enabled must be true for band_spec manifests")
        if validation.require_band_spec and not band_spec.enabled:
            errors.append("validation.require_band_spec=true requires band_spec.enabled=true")
        if validation.require_sampled_curve and canonical.kind != ContentKind.SAMPLED_CURVE:
            errors.append(
                "validation.require_sampled_curve=true requires canonical.kind=sampled_curve"
            )
        if approximation and not approximation_reason:
            errors.append("approximation_reason is required when approximation=true")
        if curve_realization.approximation and not curve_realization.enabled:
            errors.append("curve_realization.approximation=true requires curve_realization.enabled=true")
        if errors:
            raise ManifestValidationError(errors)

        return cls(
            source_id=source_id,
            sensor_unit_id=sensor_unit_id,
            representation_variant=representation_variant,
            source_tier=source_tier,
            source_type=source_type,
            content_kind=content_kind,
            mission_family=mission_family,
            platform=platform,
            instrument=instrument,
            approximation=approximation,
            approximation_reason=approximation_reason,
            title=title,
            url=url,
            retrieved_at=retrieved_at,
            doc_version=doc_version,
            raw_local_path=raw_local_path,
            file_sha256=file_sha256,
            license_note=license_note,
            parser=parser,
            canonical=canonical,
            band_spec=band_spec,
            curve_realization=curve_realization,
            validation=validation,
            notes=tuple(notes),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "sensor_unit_id": self.sensor_unit_id,
            "representation_variant": self.representation_variant,
            "source_tier": self.source_tier.value,
            "source_type": self.source_type.value,
            "content_kind": self.content_kind.value,
            "mission_family": self.mission_family,
            "platform": self.platform,
            "instrument": self.instrument,
            "approximation": self.approximation,
            "approximation_reason": self.approximation_reason,
            "title": self.title,
            "url": self.url,
            "retrieved_at": self.retrieved_at,
            "doc_version": self.doc_version,
            "raw_local_path": self.raw_local_path,
            "file_sha256": self.file_sha256,
            "license_note": self.license_note,
            "parser": self.parser.to_dict(),
            "canonical": self.canonical.to_dict(),
            "band_spec": self.band_spec.to_dict(),
            "curve_realization": self.curve_realization.to_dict(),
            "validation": self.validation.to_dict(),
            "notes": list(self.notes),
        }

    def summary(self) -> ManifestSummary:
        return ManifestSummary.from_manifest(self)


def enum_values(enum_cls: type[Enum]) -> set[str]:
    """Return the set of serialized enum values."""

    return {str(member.value) for member in enum_cls}  # type: ignore[arg-type]


def as_dict_without_none(payload: Mapping[str, Any]) -> Dict[str, Any]:
    """Drop null values from nested metadata dictionaries."""

    cleaned: Dict[str, Any] = {}
    for key, value in payload.items():
        if value is None:
            continue
        if isinstance(value, Mapping):
            cleaned[key] = as_dict_without_none(value)
            continue
        cleaned[key] = value
    return cleaned


def _is_placeholder(value: Any) -> bool:
    return isinstance(value, str) and value.startswith("<") and value.endswith(">")


def _enum_from_string(
    enum_cls: type[Enum],
    raw_value: str,
    errors: list[str],
    field_name: str,
) -> Any:
    if not raw_value:
        return None
    try:
        return enum_cls(raw_value)
    except ValueError:
        errors.append(
            f"{field_name} must be one of {sorted(enum_values(enum_cls))}; got {raw_value!r}"
        )
        return None


def _required_mapping(
    payload: Mapping[str, Any],
    key: str,
    errors: list[str],
    prefix: str = "",
) -> Mapping[str, Any]:
    value = payload.get(key)
    full_name = _join_prefix(prefix, key)
    if not isinstance(value, Mapping):
        errors.append(f"{full_name} must be an object")
        return {}
    return value


def _required_string(
    payload: Mapping[str, Any],
    key: str,
    errors: list[str],
    prefix: str = "",
) -> str:
    value = payload.get(key)
    full_name = _join_prefix(prefix, key)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{full_name} must be a non-empty string")
        return ""
    return value


def _optional_string(
    payload: Mapping[str, Any],
    key: str,
    errors: list[str],
    prefix: str = "",
) -> Optional[str]:
    value = payload.get(key)
    full_name = _join_prefix(prefix, key)
    if value is None:
        return None
    if not isinstance(value, str):
        errors.append(f"{full_name} must be a string or null")
        return None
    return value


def _required_string_list(
    payload: Mapping[str, Any],
    key: str,
    errors: list[str],
    prefix: str = "",
) -> list[str]:
    value = payload.get(key)
    full_name = _join_prefix(prefix, key)
    if not isinstance(value, list):
        errors.append(f"{full_name} must be a list of strings")
        return []
    items: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str):
            errors.append(f"{full_name}[{index}] must be a string")
            continue
        items.append(item)
    return items


def _optional_string_list(
    payload: Mapping[str, Any],
    key: str,
    errors: list[str],
    prefix: str = "",
) -> list[str]:
    if key not in payload or payload.get(key) is None:
        return []
    return _required_string_list(payload, key, errors, prefix)


def _optional_string_mapping(
    payload: Mapping[str, Any],
    key: str,
    errors: list[str],
    prefix: str = "",
) -> Mapping[str, str]:
    value = payload.get(key)
    full_name = _join_prefix(prefix, key)
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        errors.append(f"{full_name} must be an object")
        return {}
    items: Dict[str, str] = {}
    for nested_key, nested_value in value.items():
        if not isinstance(nested_key, str):
            errors.append(f"{full_name} contains a non-string key")
            continue
        if not isinstance(nested_value, str):
            errors.append(f"{full_name}.{nested_key} must be a string")
            continue
        items[nested_key] = nested_value
    return items


def _required_bool(
    payload: Mapping[str, Any],
    key: str,
    errors: list[str],
    prefix: str = "",
) -> bool:
    value = payload.get(key)
    full_name = _join_prefix(prefix, key)
    if not isinstance(value, bool):
        errors.append(f"{full_name} must be a boolean")
        return False
    return value


def _required_int(
    payload: Mapping[str, Any],
    key: str,
    errors: list[str],
    prefix: str = "",
) -> int:
    value = payload.get(key)
    full_name = _join_prefix(prefix, key)
    if isinstance(value, bool) or not isinstance(value, int):
        errors.append(f"{full_name} must be an integer")
        return 0
    return value


def _required_float(
    payload: Mapping[str, Any],
    key: str,
    errors: list[str],
    prefix: str = "",
) -> float:
    value = payload.get(key)
    full_name = _join_prefix(prefix, key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        errors.append(f"{full_name} must be a float")
        return 0.0
    return float(value)


def _required_int_or_placeholder(
    payload: Mapping[str, Any],
    key: str,
    errors: list[str],
    prefix: str = "",
) -> int | str:
    value = payload.get(key)
    full_name = _join_prefix(prefix, key)
    if isinstance(value, bool):
        errors.append(f"{full_name} must be an integer or placeholder string")
        return ""
    if isinstance(value, int):
        return value
    if _is_placeholder(value):
        return value
    errors.append(f"{full_name} must be an integer or placeholder string")
    return ""


def _join_prefix(prefix: str, key: str) -> str:
    return f"{prefix}.{key}" if prefix else key
