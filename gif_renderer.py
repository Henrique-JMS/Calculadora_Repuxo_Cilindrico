"""
gif_renderer.py
===============
Generates an animated GIF showing the full (mirrored) cross-section of every
deep-drawing stage, from blank to final flanged cup.

Each frame is a full mirrored view (left + right halves) using the same
geometric logic as renderer.py, composited into a smooth animation.

Usage:
    from gif_renderer import generate_animation_gif

    gif_bytes = generate_animation_gif(blank_res, seq_res, t=1.5, d_f=120.0, d_i=80.0)
    st.image(gif_bytes)
"""

from __future__ import annotations

import io
import math
from typing import Dict, List

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

from blank_calculator import BlankResult
from pass_sequence import PassSequenceResult, PassData
from renderer import (
    _blank_fill_polygon,
    _blank_profile,
    _COLOR_AXIS,
    _COLOR_BG,
    _COLOR_CONTOUR,
    _COLOR_DIM,
    _COLOR_FILL,
    _cup_fill_polygon,
    _cup_profile,
    _cup_radii,
    _LINE_W_AXIS,
    _LINE_W_PROFILE,
    _make_figure,
)

# ---------------------------------------------------------------------------
# Matplotlib → PIL conversion
# ---------------------------------------------------------------------------

def _fig_to_pil(fig: plt.Figure) -> Image.Image:
    """Render a matplotlib figure to an RGB PIL Image."""
    buf = io.BytesIO()
    fig.savefig(
        buf, format="png", dpi=100,
        bbox_inches="tight",
        facecolor=fig.get_facecolor(),
        edgecolor="none",
    )
    buf.seek(0)
    return Image.open(buf).convert("RGB")


# ---------------------------------------------------------------------------
# Full mirrored stage renderers
# ---------------------------------------------------------------------------

def _render_full_blank(
    ax: plt.Axes,
    blank_res: BlankResult,
    t: float,
    pad_x: float,
    pad_y_top: float,
    pad_y_bot: float,
) -> None:
    """Draw the blank as a full mirrored cross-section on *ax*."""
    d = blank_res.d_blank_final
    r = d / 2.0

    ax.set_title("Blank", fontsize=12, fontweight="bold", pad=10)

    # Fill (right + mirrored left)
    px, py = _blank_fill_polygon(d, t)
    ax.fill(px,  py, color=_COLOR_FILL, alpha=0.75, zorder=2)
    ax.fill(-px, py, color=_COLOR_FILL, alpha=0.75, zorder=2)

    # Contour (right + mirrored left)
    for xs, ys in _blank_profile(d, t):
        if np.all(np.abs(xs) < 1e-9):
            continue                                                 # skip axis-line segments
        ax.plot(xs,  ys, color=_COLOR_CONTOUR, lw=_LINE_W_PROFILE,
                solid_capstyle="round", zorder=3)
        ax.plot(-xs, ys, color=_COLOR_CONTOUR, lw=_LINE_W_PROFILE,
                solid_capstyle="round", zorder=3)

    # Axis line
    ax.plot([0, 0], [-t * 0.5, t * 1.15], color=_COLOR_AXIS,
            lw=_LINE_W_AXIS, linestyle=(0, (8, 3, 2, 3)), zorder=1)

    # Info box
    info = (f"Blank: \u2300 {d:.1f} mm\n"
            f"t = {t:.2f} mm  |  t/D = {blank_res.t_D_ratio_pct:.2f}%")
    ax.text(0.02, 0.02, info, transform=ax.transAxes,
            fontsize=8, va="bottom", fontfamily="monospace",
            color="#333333",
            bbox=dict(boxstyle="round,pad=0.4", fc="white", alpha=0.7))

    ax.set_xlim(-pad_x, pad_x)
    ax.set_ylim(pad_y_bot, pad_y_top)


def _render_full_pass(
    ax: plt.Axes,
    pd: PassData,
    t: float,
    flange_d: float,
    pad_x: float,
    pad_y_top: float,
    pad_y_bot: float,
) -> None:
    """Draw one drawing pass as a full mirrored cross-section on *ax*."""
    is_last = pd.is_final
    title = f"Passe {pd.pass_number}" + ("  \u2014 Final" if is_last else "")
    ax.set_title(title, fontsize=12, fontweight="bold", pad=10)

    # Fill (right + mirrored left)
    rx, ry = _cup_fill_polygon(pd, t, flange_d)
    ax.fill(rx,  ry, color=_COLOR_FILL, alpha=0.75, zorder=2)
    ax.fill(-rx, ry, color=_COLOR_FILL, alpha=0.75, zorder=2)

    # Contour (right + mirrored left)
    for xs, ys in _cup_profile(pd, t, flange_d):
        if np.all(np.abs(xs) < 1e-9):
            continue                                                 # skip axis-line segments
        ax.plot(xs,  ys, color=_COLOR_CONTOUR, lw=_LINE_W_PROFILE,
                solid_capstyle="round", zorder=3)
        ax.plot(-xs, ys, color=_COLOR_CONTOUR, lw=_LINE_W_PROFILE,
                solid_capstyle="round", zorder=3)

    # Axis line
    H = pd.height
    ax.plot([0, 0], [-t * 0.5, H * 1.15], color=_COLOR_AXIS,
            lw=_LINE_W_AXIS, linestyle=(0, (8, 3, 2, 3)), zorder=1)

    # Severity-coloured info box
    sev_map: Dict[str, str] = {
        "green": "#2E7D32", "yellow": "#F57F17", "red": "#C62828",
    }
    sev = sev_map.get(pd.severity, "#333333")
    info = (f"DR = {pd.drawing_ratio:.3f}  |  m = {pd.drawing_coeff:.3f}\n"
            f"H = {pd.height:.1f} mm  |  \u2300i = {pd.d_after * 2 - 2 * t:.1f} mm")
    ax.text(0.02, 0.02, info, transform=ax.transAxes,
            fontsize=8, va="bottom", fontfamily="monospace",
            color=sev,
            bbox=dict(boxstyle="round,pad=0.4", fc="white", alpha=0.8))

    ax.set_xlim(-pad_x, pad_x)
    ax.set_ylim(pad_y_bot, pad_y_top)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_animation_gif(
    blank_res: BlankResult,
    seq_res: PassSequenceResult,
    t: float,
    d_f: float,
    d_i: float,
    fps: float = 1.0,
    final_hold: float = 2.0,
) -> bytes:
    """
    Generate an animated GIF of all deep-drawing stages.

    Each frame shows the full mirrored cross-section of one stage
    (blank or drawing pass), using consistent axis limits so the
    animation does not jump between frames.

    Args:
        blank_res : BlankResult from blank_calculator.compute_blank().
        seq_res   : PassSequenceResult from pass_sequence.compute_pass_sequence().
        t         : Sheet thickness (mm).
        d_f       : Flange outer diameter of finished part (mm).
        d_i       : Internal diameter of finished part (mm).
        fps       : Frames per second (default 1.0 → 1 s per frame).
        final_hold: Extra seconds to hold the last frame (default 2.0).

    Returns:
        GIF file content as bytes.
    """
    passes = seq_res.passes
    if not passes:
        raise ValueError("Pass sequence is empty \u2014 nothing to animate.")

    # ------------------------------------------------------------------ #
    # Compute global axis limits so all frames share the same boundaries  #
    # ------------------------------------------------------------------ #

    # Blank half-width
    r_blank = blank_res.d_blank_final / 2.0

    # Max cup radial extent across all passes
    r_cup = max(
        max(
            pd.flange_diameter / 2.0,
            pd.d_after / 2.0 + t,
        )
        for pd in passes
    )

    # Max height across all passes
    H_cup = max(pd.height for pd in passes)

    global_max_r = max(r_blank, r_cup)
    global_H     = max(t, H_cup)

    # Consistent aspect ratio for all frames
    ar = max(0.7, min(2.0, (global_H + t * 4) / (global_max_r * 2.5)))

    # Axis padding (consistent across all frames)
    pad_x     = global_max_r * 1.35
    pad_y_top = global_H * 1.2
    pad_y_bot = -t * 8

    # ------------------------------------------------------------------ #
    # Render frames                                                       #
    # ------------------------------------------------------------------ #

    frames: List[Image.Image] = []
    durations: List[int] = []

    # Blank frame
    fig, ax = _make_figure(aspect_ratio=ar)
    _render_full_blank(ax, blank_res, t, pad_x, pad_y_top, pad_y_bot)
    fig.tight_layout()
    frames.append(_fig_to_pil(fig))
    durations.append(int(1000.0 / fps))
    plt.close(fig)

    # Pass frames
    for pd in passes:
        fig, ax = _make_figure(aspect_ratio=ar)
        flange = d_f if pd.is_final else pd.flange_diameter
        _render_full_pass(ax, pd, t, flange, pad_x, pad_y_top, pad_y_bot)
        fig.tight_layout()
        frames.append(_fig_to_pil(fig))
        durations.append(int(1000.0 / fps))
        plt.close(fig)

    # Hold the last frame longer
    durations[-1] += int(final_hold * 1000.0)

    # ------------------------------------------------------------------ #
    # Compose GIF                                                         #
    # ------------------------------------------------------------------ #

    out = io.BytesIO()
    frames[0].save(
        out,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        loop=0,
        duration=durations,
        optimize=True,
    )
    out.seek(0)
    return out.read()
