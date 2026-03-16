"""Plotting helpers for sampled curves."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

import numpy as np

from .models import BandSpec, SampledCurve


def _load_pyplot():
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise RuntimeError("matplotlib is required for plotting") from exc
    return plt


def plot_curve(curve: SampledCurve, *, output_path: Path | None = None) -> Path | None:
    """Plot a sampled curve using matplotlib if available."""

    plt = _load_pyplot()

    wavelength_nm = np.asarray(curve.wavelength_nm, dtype=float)
    response = np.asarray(curve.response, dtype=float)

    figure, axis = plt.subplots(figsize=(7, 4))
    axis.plot(wavelength_nm, response, linewidth=2.0)
    axis.set_xlabel("Wavelength (nm)")
    axis.set_ylabel("Relative response")
    axis.set_title(curve.band_id)
    axis.grid(True, alpha=0.25)
    figure.tight_layout()

    if output_path is None:
        return None

    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=150)
    plt.close(figure)
    return output_path


def plot_curve_collection(
    curves: Sequence[SampledCurve],
    *,
    output_path: Path,
    title: str | None = None,
) -> Path:
    """Plot an overview of multiple sampled curves."""

    if not curves:
        raise ValueError("at least one curve is required")

    plt = _load_pyplot()
    figure, axis = plt.subplots(figsize=(9, 5))
    color_map = plt.get_cmap("tab20")

    for index, curve in enumerate(curves):
        wavelength_nm = np.asarray(curve.wavelength_nm, dtype=float)
        response = np.asarray(curve.response, dtype=float)
        axis.plot(
            wavelength_nm,
            response,
            linewidth=1.5,
            label=curve.band_id,
            color=color_map(index % 20),
        )

    axis.set_xlabel("Wavelength (nm)")
    axis.set_ylabel("Relative response")
    axis.set_title(title or "Sampled curve overview")
    axis.grid(True, alpha=0.25)
    axis.legend(ncol=2, fontsize=8)
    figure.tight_layout()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=150)
    plt.close(figure)
    return output_path


def plot_curve_overlays(
    curve_pairs: Sequence[tuple[SampledCurve, SampledCurve]],
    *,
    output_path: Path,
    title: str | None = None,
) -> Path:
    """Plot canonical curves against trusted overlay references."""

    if not curve_pairs:
        raise ValueError("at least one curve pair is required")

    plt = _load_pyplot()
    figure, axis = plt.subplots(figsize=(9, 5))
    color_map = plt.get_cmap("tab20")

    for index, (curve, reference_curve) in enumerate(curve_pairs):
        color = color_map(index % 20)
        curve_wavelength_nm = np.asarray(curve.wavelength_nm, dtype=float)
        curve_response = np.asarray(curve.response, dtype=float)
        reference_wavelength_nm = np.asarray(reference_curve.wavelength_nm, dtype=float)
        reference_response = np.asarray(reference_curve.response, dtype=float)
        axis.plot(
            curve_wavelength_nm,
            curve_response,
            linewidth=1.5,
            color=color,
            label=f"{curve.band_id} canonical",
        )
        axis.plot(
            reference_wavelength_nm,
            reference_response,
            linewidth=1.0,
            linestyle="--",
            color=color,
            label=f"{reference_curve.band_id} reference",
        )

    axis.set_xlabel("Wavelength (nm)")
    axis.set_ylabel("Relative response")
    axis.set_title(title or "Curve overlay")
    axis.grid(True, alpha=0.25)
    axis.legend(ncol=2, fontsize=8)
    figure.tight_layout()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=150)
    plt.close(figure)
    return output_path


def plot_band_spec_summary(
    band_specs: Sequence[BandSpec],
    *,
    output_path: Path,
    title: str | None = None,
) -> Path:
    """Plot band centers with FWHM error bars for metadata-only sensors."""

    if not band_specs:
        raise ValueError("at least one band specification is required")

    plt = _load_pyplot()
    ordered_band_specs = sorted(
        band_specs,
        key=lambda band_spec: (
            band_spec.band_index if band_spec.band_index is not None else 10**9,
            band_spec.band_id,
        ),
    )
    y_positions = np.arange(len(ordered_band_specs), dtype=float)
    centers = np.asarray(
        [band_spec.center_wavelength_nm for band_spec in ordered_band_specs],
        dtype=float,
    )
    half_widths = np.asarray(
        [band_spec.fwhm_nm / 2.0 for band_spec in ordered_band_specs],
        dtype=float,
    )
    labels = [band_spec.band_id for band_spec in ordered_band_specs]
    status_colors = {
        "nominal": "#1f77b4",
        "recommended": "#2ca02c",
        "masked": "#7f7f7f",
    }
    colors = [
        status_colors.get(band_spec.band_status, "#ff7f0e")
        for band_spec in ordered_band_specs
    ]

    figure, axis = plt.subplots(figsize=(9, 5))
    for y_position, center, half_width, label, color in zip(
        y_positions,
        centers,
        half_widths,
        labels,
        colors,
    ):
        axis.errorbar(
            center,
            y_position,
            xerr=half_width,
            fmt="o",
            color=color,
            capsize=4,
        )
        axis.text(center + half_width + 1.0, y_position, label, va="center", fontsize=8)

    axis.set_xlabel("Center wavelength (nm)")
    axis.set_ylabel("Band index")
    axis.set_yticks(y_positions)
    axis.set_yticklabels(
        [
            str(band_spec.band_index if band_spec.band_index is not None else index + 1)
            for index, band_spec in enumerate(ordered_band_specs)
        ]
    )
    axis.set_title(title or "Band-spec overview")
    axis.grid(True, axis="x", alpha=0.25)
    axis.invert_yaxis()
    figure.tight_layout()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=150)
    plt.close(figure)
    return output_path
