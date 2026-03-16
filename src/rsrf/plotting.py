"""Plotting helpers for sampled curves."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from .models import SampledCurve


def plot_curve(curve: SampledCurve, *, output_path: Path | None = None) -> Path | None:
    """Plot a sampled curve using matplotlib if available."""

    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise RuntimeError("matplotlib is required for plotting") from exc

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
