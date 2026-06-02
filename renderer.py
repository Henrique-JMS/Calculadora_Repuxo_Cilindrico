"""
renderer.py
===========
Renders the deep drawing stage profiles using matplotlib, suitable for
inline display in the Streamlit interface.

Each stage (blank + N passes) is rendered as a right-half axisymmetric
cross-section. The renderer re-uses the same geometric logic as
dxf_generator.py but targets matplotlib primitives instead of DXF entities.

Usage:
    from renderer import render_all_stages

    figures = render_all_stages(blank_res, seq_res, t=1.5, d_f=120.0, d_i=80.0)
    for fig in figures:
        st.pyplot(fig)
        plt.close(fig)

References:
    - PRD §7.5 — Pré-visualização no Streamlit
"""

from __future__ import annotations

import math
from typing import List, Optional, Tuple

import matplotlib
matplotlib.use("Agg")                        # headless backend
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
import numpy as np

from blank_calculator import BlankResult
from pass_sequence import PassSequenceResult, PassData

# ---------------------------------------------------------------------------
# Visual style constants
# ---------------------------------------------------------------------------

_COLOR_CONTOUR = "#2C2C2C"   # near-black for profile lines
_COLOR_AXIS    = "#CC3333"   # red for symmetry axis
_COLOR_DIM     = "#4444AA"   # blue for dimension annotations
_COLOR_FILL    = "#D0E8F2"   # light blue fill for material cross-section
_COLOR_BG      = "#FAFAFA"   # figure background

_LINE_W_PROFILE = 1.8   # profile line width
_LINE_W_AXIS    = 1.0   # axis line width
_LINE_W_DIM     = 0.7   # dimension line width

_ARC_PTS = 80           # number of points used to approximate each arc


# ---------------------------------------------------------------------------
# Geometric helpers (shared with DXF generator, but in numpy)
# ---------------------------------------------------------------------------

def _arc_xy(cx: float, cy: float, r: float,
            start_deg: float, end_deg: float,
            n: int = _ARC_PTS) -> Tuple[np.ndarray, np.ndarray]:
    """
    Return (x, y) arrays for a CCW arc from start_deg to end_deg.

    If end_deg < start_deg the arc wraps through 360° (CCW).
    This mirrors ezdxf's arc convention exactly.

    Args:
        cx, cy    : arc centre
        r         : radius
        start_deg : start angle in degrees (CCW from +x axis)
        end_deg   : end angle in degrees
        n         : number of interpolation points

    Returns:
        Tuple of (x_array, y_array).
    """
    if end_deg <= start_deg:
        end_deg += 360.0
    theta = np.linspace(math.radians(start_deg), math.radians(end_deg), n)
    return cx + r * np.cos(theta), cy + r * np.sin(theta)


def _cup_radii(d_after: float, t: float) -> Tuple[float, float]:
    """Return (r_inner, r_outer) from the neutral cup diameter and thickness."""
    r_n = d_after / 2.0
    return r_n - t / 2.0, r_n + t / 2.0


# ---------------------------------------------------------------------------
# Profile builders (return lists of (x_array, y_array) segments)
# ---------------------------------------------------------------------------

def _blank_profile(d_blank: float, t: float
                   ) -> List[Tuple[np.ndarray, np.ndarray]]:
    """
    Right-half cross-section of the flat blank (a rectangle).

    Returns list of (x, y) line segments forming the closed profile.
    """
    r = d_blank / 2.0
    segs = [
        (np.array([0, r]), np.array([0, 0])),     # bottom
        (np.array([r, r]), np.array([0, t])),     # outer edge
        (np.array([r, 0]), np.array([t, t])),     # top
        (np.array([0, 0]), np.array([t, 0])),     # axis boundary
    ]
    return segs


def _blank_fill_polygon(d_blank: float, t: float
                        ) -> Tuple[np.ndarray, np.ndarray]:
    """Closed polygon coords for filling the blank cross-section."""
    r = d_blank / 2.0
    px = np.array([0, r, r, 0, 0])
    py = np.array([0, 0, t, t, 0])
    return px, py


def _cup_profile(pd: PassData, t: float, d_f: Optional[float] = None
                 ) -> List[Tuple[np.ndarray, np.ndarray]]:
    """
    Right-half cross-section segments of a drawn cup for one pass.

    Segments form a closed profile (CCW winding when traversed in order).

    Args:
        pd  : PassData for this pass.
        t   : Sheet thickness (mm).
        d_f : Flange outer diameter (mm); None = no flange (intermediate).

    Returns:
        List of (x_array, y_array) segments.
    """
    r_i, r_o = _cup_radii(pd.d_after, t)
    H   = pd.height
    r_p = min(pd.r_punch, r_i * 0.99)
    r_m = pd.r_die
    r_f = d_f / 2.0 if d_f is not None else None

    segs: List[Tuple[np.ndarray, np.ndarray]] = []

    # ---- INNER SURFACE (bottom → top) ------------------------------------

    # 1. Flat inner bottom
    segs.append((np.array([0.0, r_i - r_p]), np.array([0.0, 0.0])))

    # 2. Inner punch fillet (CCW 270° → 360°)
    ax, ay = _arc_xy(r_i - r_p, r_p, r_p, 270, 360)
    segs.append((ax, ay))

    # 3. Inner wall — shortened by r_die
    segs.append((np.array([r_i, r_i]), np.array([r_p, H - r_m])))

    # 3b. Die fillet on inner surface (wall → flange top)
    #     centre: (r_i + r_m, H - r_m), CCW 90° → 180°
    ax, ay = _arc_xy(r_i + r_m, H - r_m, r_m, 90, 180)
    segs.append((ax, ay))

    # 4. Flange top or rim — shortened by r_die
    if r_f is not None:
        segs.append((np.array([r_i + r_m, r_f]), np.array([H, H])))
    else:
        segs.append((np.array([r_i + r_m, r_o]), np.array([H, H])))

    # ---- OUTER SURFACE (top → bottom) ------------------------------------

    if r_f is not None:
        # 5. Outer flange edge
        segs.append((np.array([r_f, r_f]), np.array([H, H - t])))

        # 6. Flange bottom
        die_tp_x = r_o + r_m
        segs.append((np.array([r_f, die_tp_x]), np.array([H - t, H - t])))

        # 7. Die fillet (flange bottom → wall, fillet, CCW 90° → 180°)
        ax, ay = _arc_xy(r_o + r_m, H - t - r_m, r_m, 90, 180)
        segs.append((ax, ay))

        # 8. Outer wall (below die fillet to outer punch fillet)
        segs.append((np.array([r_o, r_o]), np.array([H - t - r_m, r_p])))

    else:
        # Intermediate: outer wall from rim
        segs.append((np.array([r_o, r_o]), np.array([H, r_p])))

    # 9. Outer punch fillet (CCW 270° → 360°)
    ax, ay = _arc_xy(r_i - r_p, r_p, r_p + t, 270, 360)
    segs.append((ax, ay))

    # 10. Outer bottom
    segs.append((np.array([r_i - r_p, 0.0]), np.array([-t, -t])))

    # 11. Close at axis boundary
    segs.append((np.array([0.0, 0.0]), np.array([-t, 0.0])))

    return segs


def _cup_fill_polygon(pd: PassData, t: float, d_f: Optional[float] = None,
                      n_arc: int = _ARC_PTS
                      ) -> Tuple[np.ndarray, np.ndarray]:
    """
    Build a closed (x, y) polygon for filling the cup cross-section.

    Traverses the profile CCW: inner surface (bottom → top),
    then outer surface (top → bottom), closing at the axis.
    """
    r_i, r_o = _cup_radii(pd.d_after, t)
    H   = pd.height
    r_p = min(pd.r_punch, r_i * 0.99)
    r_m = pd.r_die
    r_f = d_f / 2.0 if d_f is not None else None

    xs, ys = [], []

    def _add(x, y):
        if isinstance(x, np.ndarray):
            xs.extend(x.tolist())
            ys.extend(y.tolist())
        else:
            xs.append(x)
            ys.append(y)

    # Inner surface (CCW)
    _add(0.0, 0.0)
    _add(r_i - r_p, 0.0)
    ax, ay = _arc_xy(r_i - r_p, r_p, r_p, 270, 360, n_arc)
    _add(ax, ay)
    _add(r_i, H - r_m)         # shortened inner wall
    # Upper die fillet — reversed: wall (r_i, H-r_m) → flange (r_i+r_m, H)
    ax, ay = _arc_xy(r_i + r_m, H - r_m, r_m, 90, 180, n_arc)
    _add(ax[::-1], ay[::-1])

    if r_f is not None:
        _add(r_f, H)
        _add(r_f, H - t)
        # Lower die fillet — flange (r_o+r_m, H-t) → wall (r_o, H-t-r_m)
        # CCW 90°→180° goes from flange to wall
        ax, ay = _arc_xy(r_o + r_m, H - t - r_m, r_m, 90, 180, n_arc)
        _add(ax, ay)
        _add(r_o, r_p)
    else:
        _add(r_o, H)
        _add(r_o, r_p)

    # Outer punch fillet — reversed: wall (ro, rp) → bottom (ri-rp, -t)
    # 270°→360° goes bottom→wall, reversal makes it wall→bottom for the polygon
    ax, ay = _arc_xy(r_i - r_p, r_p, r_p + t, 270, 360, n_arc)
    _add(ax[::-1], ay[::-1])
    _add(0.0, -t)
    _add(0.0, 0.0)   # close

    return np.array(xs), np.array(ys)


# ---------------------------------------------------------------------------
# Figure builders
# ---------------------------------------------------------------------------

def _make_figure(aspect_ratio: float = 1.0) -> Tuple[plt.Figure, plt.Axes]:
    """Create a styled figure and axes."""
    fig, ax = plt.subplots(figsize=(6, 6 * aspect_ratio), dpi=110)
    fig.patch.set_facecolor(_COLOR_BG)
    ax.set_facecolor(_COLOR_BG)
    ax.set_aspect("equal")
    ax.grid(False)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(left=False, bottom=False,
                   labelleft=False, labelbottom=False)
    return fig, ax


def _draw_axis_line(ax: plt.Axes, y_min: float, y_max: float,
                    x: float = 0.0) -> None:
    """Draw the symmetry axis centre line."""
    ax.axvline(x=x, ymin=0, ymax=1, color=_COLOR_AXIS,
               linewidth=_LINE_W_AXIS, linestyle=(0, (8, 3, 2, 3)),
               zorder=1)


def _add_dim_annotation(ax: plt.Axes, text: str,
                        x: float, y: float, ha: str = "center") -> None:
    """Add a compact dimension text annotation."""
    ax.text(x, y, text, ha=ha, va="center",
            fontsize=7.5, color=_COLOR_DIM,
            fontfamily="monospace")


def render_blank(blank_res: BlankResult, t: float) -> plt.Figure:
    """
    Render the blank stage as a matplotlib figure.

    Args:
        blank_res : BlankResult from blank_calculator.compute_blank().
        t         : Sheet thickness (mm).

    Returns:
        matplotlib Figure object.
    """
    d = blank_res.d_blank_final
    r = d / 2.0

    fig, ax = _make_figure(aspect_ratio=0.5)
    ax.set_title("Blank", fontsize=12, fontweight="bold", pad=10)

    # Fill
    px, py = _blank_fill_polygon(d, t)
    ax.fill(px, py, color=_COLOR_FILL, alpha=0.7, zorder=2)

    # Contour
    for xs, ys in _blank_profile(d, t):
        ax.plot(xs, ys, color=_COLOR_CONTOUR, lw=_LINE_W_PROFILE, zorder=3)

    # Axis line
    _draw_axis_line(ax, -t * 3, t * 3)

    # Annotations
    margin = t * 4
    _add_dim_annotation(ax, f"⌀ {d:.1f} mm", r / 2, t + margin)
    _add_dim_annotation(ax, f"t = {t:.2f} mm", r + t * 2, t / 2, ha="left")

    # Info box
    info = (f"Blank Final: ⌀ {d:.1f} mm\n"
            f"Área: {blank_res.area_blank:.0f} mm²\n"
            f"t/D = {blank_res.t_D_ratio_pct:.2f}%")
    ax.text(0.02, 0.02, info, transform=ax.transAxes,
            fontsize=7.5, va="bottom", fontfamily="monospace",
            color="#333333",
            bbox=dict(boxstyle="round,pad=0.4", fc="white", alpha=0.7))

    # Padding
    ax.set_xlim(-r * 0.15, r * 1.25)
    ax.set_ylim(-t * 6, t * 10)
    fig.tight_layout()
    return fig


def render_pass(pd: PassData, t: float,
                d_f: Optional[float] = None,
                d_i: Optional[float] = None) -> plt.Figure:
    """
    Render a single drawing pass stage as a matplotlib figure.

    Args:
        pd  : PassData for this pass.
        t   : Sheet thickness (mm).
        d_f : Flange outer diameter (mm); None for intermediate passes.
        d_i : Internal diameter of the finished cup (mm) — used for annotation.

    Returns:
        matplotlib Figure object.
    """
    r_i, r_o = _cup_radii(pd.d_after, t)
    H   = pd.height
    r_f = d_f / 2.0 if d_f is not None else r_o
    max_r = max(r_f, r_o)

    is_last = pd.is_final
    title = f"Passe {pd.pass_number}" + (" — Final" if is_last else "")

    # Aspect ratio: tall cups → taller figure
    ar = max(0.8, min(2.0, (H + t * 4) / (max_r * 2.2)))
    fig, ax = _make_figure(aspect_ratio=ar)
    ax.set_title(title, fontsize=12, fontweight="bold", pad=10)

    # Fill
    px, py = _cup_fill_polygon(pd, t, d_f)
    ax.fill(px, py, color=_COLOR_FILL, alpha=0.75, zorder=2)

    # Contour lines
    for xs, ys in _cup_profile(pd, t, d_f):
        ax.plot(xs, ys, color=_COLOR_CONTOUR, lw=_LINE_W_PROFILE,
                solid_capstyle="round", zorder=3)

    # Axis line
    _draw_axis_line(ax, -t * 2, H * 1.15)

    # ---- Annotations -------------------------------------------------------
    ann_x_right = max_r + r_i * 0.12

    # Inner diameter
    ax.annotate("", xy=(r_i, -t * 1.8), xytext=(0, -t * 1.8),
                arrowprops=dict(arrowstyle="<->", color=_COLOR_DIM, lw=0.8))
    _add_dim_annotation(ax, f"⌀i {r_i * 2:.1f}", r_i / 2, -t * 2.5)

    # Flange diameter (final only)
    if d_f is not None:
        ax.annotate("", xy=(r_f, -t * 4.5), xytext=(0, -t * 4.5),
                    arrowprops=dict(arrowstyle="<->", color=_COLOR_DIM, lw=0.8))
        _add_dim_annotation(ax, f"⌀f {d_f:.1f}", r_f / 2, -t * 5.5)

    # Height
    ax.annotate("", xy=(ann_x_right, H), xytext=(ann_x_right, 0),
                arrowprops=dict(arrowstyle="<->", color=_COLOR_DIM, lw=0.8))
    _add_dim_annotation(ax, f"H {H:.1f}", ann_x_right + r_i * 0.18, H / 2,
                        ha="left")

    # ---- Info box ----------------------------------------------------------
    sev_color = {"green": "#2E7D32", "yellow": "#F57F17", "red": "#C62828"}
    sev = sev_color.get(pd.severity, "#333333")

    info = (f"DR = {pd.drawing_ratio:.3f}\n"
            f"m  = {pd.drawing_coeff:.3f}\n"
            f"Red. = {pd.reduction_pct:.1f}%\n"
            f"r_die = {pd.r_die:.1f} mm")
    ax.text(0.02, 0.98, info, transform=ax.transAxes,
            fontsize=7.5, va="top", fontfamily="monospace",
            color=sev,
            bbox=dict(boxstyle="round,pad=0.4", fc="white", alpha=0.8))

    # Padding
    ax.set_xlim(-max_r * 0.18, max_r * 1.35)
    ax.set_ylim(-t * 8, H * 1.2)
    fig.tight_layout()
    return fig


def render_final_part_full(
    d_i: float,
    H: float,
    d_f: float,
    t: float,
    r_punch: float,
    r_die: float,
) -> plt.Figure:
    """
    Render a full (mirrored) cross-section drawing of the final flanged cup
    with all dimension annotations. Unlike the per-pass figures which show
    only the right half, this function mirrors the profile across the
    symmetry axis to produce a complete aesthetic view of the finished part.

    This figure is intended for display at the top of the Streamlit app and
    is NOT exported to DXF.

    Args:
        d_i     : Internal diameter of finished cup (mm).
        H       : Wall height of finished cup (mm).
        d_f     : Flange outer diameter (mm).
        t       : Sheet thickness (mm).
        r_punch : Punch corner radius (mm).
        r_die   : Die corner radius (mm).

    Returns:
        matplotlib Figure object with the full mirrored cross-section.
    """
    # Build a synthetic PassData for the final part
    r_i = d_i / 2.0
    r_f = d_f / 2.0

    # Clamp punch radius to leave a flat bottom
    r_p = min(r_punch, r_i * 0.99)

    from pass_sequence import PassData as _PassData
    pd = _PassData(
        pass_number=0,
        d_before=0.0,
        d_after=d_i + t,
        d_neutral_after=d_i + t,
        height=H,
        drawing_coeff=0.0,
        drawing_ratio=0.0,
        reduction_pct=0.0,
        r_die=r_die,
        r_punch=r_p,
        severity="green",
        flange_diameter=d_f,
        is_final=True,
    )

    max_r = max(r_f, d_i / 2.0 + t)

    # Aspect ratio
    ar = max(0.7, min(2.0, (H + t * 4) / (max_r * 2.5)))
    fig, ax = _make_figure(aspect_ratio=ar)
    ax.set_title("Peça Final — Vista Completa", fontsize=13, fontweight="bold", pad=12)

    # ---- Fill (right + mirrored left) ------------------------------------
    rx, ry = _cup_fill_polygon(pd, t, d_f)
    ax.fill(rx, ry, color=_COLOR_FILL, alpha=0.75, zorder=2)   # right
    ax.fill(-rx, ry, color=_COLOR_FILL, alpha=0.75, zorder=2)   # left

    # ---- Contour (right + mirrored left) --------------------------------
    for xs, ys in _cup_profile(pd, t, d_f):
        ax.plot(xs, ys, color=_COLOR_CONTOUR, lw=_LINE_W_PROFILE,
                solid_capstyle="round", zorder=3)                 # right
        ax.plot(-xs, ys, color=_COLOR_CONTOUR, lw=_LINE_W_PROFILE,
                solid_capstyle="round", zorder=3)                 # left

    # ---- Symmetry axis (limited to part height, avoids crossing dim lines) -
    ax.plot([0, 0], [-t * 0.5, H * 1.15], color=_COLOR_AXIS,
            linewidth=_LINE_W_AXIS, linestyle=(0, (8, 3, 2, 3)), zorder=1)

    # ---- Dimensions --------------------------------------------------------

    # Internal diameter d_i (horizontal, centred below cup)
    dim_y_di = -t * 3.5
    ax.annotate("", xy=(r_i, dim_y_di), xytext=(-r_i, dim_y_di),
                arrowprops=dict(arrowstyle="<->", color=_COLOR_DIM, lw=1.0))
    _add_dim_annotation(ax, f"\u2300i {d_i:.1f} mm", 0, dim_y_di - 2.5)

    # Flange diameter d_f (horizontal, further below)
    dim_y_df = -t * 6.5
    ax.annotate("", xy=(r_f, dim_y_df), xytext=(-r_f, dim_y_df),
                arrowprops=dict(arrowstyle="<->", color=_COLOR_DIM, lw=1.0))
    _add_dim_annotation(ax, f"\u2300f {d_f:.1f} mm", 0, dim_y_df - 2.5)

    # Height H (vertical, right of profile)
    dim_x_h = max_r * 1.25
    ax.annotate("", xy=(dim_x_h, H), xytext=(dim_x_h, 0),
                arrowprops=dict(arrowstyle="<->", color=_COLOR_DIM, lw=1.0))
    _add_dim_annotation(ax, f"H {H:.1f} mm", dim_x_h + max_r * 0.12, H / 2,
                        ha="left")

    # Thickness t (callout on right flange edge)
    ax.annotate("", xy=(r_f, H), xytext=(r_f + max_r * 0.35, H + t * 4),
                arrowprops=dict(arrowstyle="->", color=_COLOR_DIM, lw=0.8,
                                connectionstyle="arc3,rad=0.2"),
                fontsize=0)
    _add_dim_annotation(ax, f"t = {t:.2f} mm",
                        r_f + max_r * 0.35, H + t * 4 + 2)

    # Punch radius r_p (right side, bottom)
    ax.annotate("", xy=(r_i - r_p * 0.3, r_p * 0.7),
                xytext=(r_i + max_r * 0.10, -t * 2),
                arrowprops=dict(arrowstyle="->", color=_COLOR_DIM, lw=0.8,
                                connectionstyle="arc3,rad=-0.3"),
                fontsize=0)
    _add_dim_annotation(ax, f"r\u209A = {r_p:.1f} mm",
                        r_i + max_r * 0.10, -t * 2 - 3, ha="left")

    # Die radius r_die (left side, top) — mirrored to avoid clashing with H dim
    ax.annotate("", xy=(-(d_i / 2.0 + t + r_die * 0.3), H - t - r_die * 0.7),
                xytext=(-max_r * 0.92, H * 0.85),
                arrowprops=dict(arrowstyle="->", color=_COLOR_DIM, lw=0.8,
                                connectionstyle="arc3,rad=-0.2"),
                fontsize=0)
    _add_dim_annotation(ax, f"r\u2098 = {r_die:.1f} mm",
                        -max_r * 0.92, H * 0.85 - 3, ha="right")

    # ---- Info box ----------------------------------------------------------
    info = (f"\u2300i {d_i:.1f} \u00d7 \u2300f {d_f:.1f} mm\n"
            f"H = {H:.1f} mm  |  t = {t:.2f} mm\n"
            f"r\u209A = {r_p:.1f}  |  r\u2098 = {r_die:.1f} mm")
    ax.text(0.02, 0.02, info, transform=ax.transAxes,
            fontsize=8, va="bottom", fontfamily="monospace",
            color="#333333",
            bbox=dict(boxstyle="round,pad=0.5", fc="white", alpha=0.8))

    # ---- Limits and layout -------------------------------------------------
    pad_x = max_r * 1.45
    pad_y_top = H * 1.15
    pad_y_bot = -t * 10
    ax.set_xlim(-pad_x, pad_x)
    ax.set_ylim(pad_y_bot, pad_y_top)
    fig.tight_layout()
    return fig


def render_all_stages(
    blank_res: BlankResult,
    seq_res: PassSequenceResult,
    t: float,
    d_f: float,
    d_i: float,
) -> List[plt.Figure]:
    """
    Render every stage (blank + all passes) and return a list of figures.

    The list is ordered: [blank_figure, pass_1_figure, ..., pass_N_figure].
    Each figure can be displayed independently via st.pyplot().

    Args:
        blank_res : BlankResult from blank_calculator.compute_blank().
        seq_res   : PassSequenceResult from pass_sequence.compute_pass_sequence().
        t         : Sheet thickness (mm).
        d_f       : Flange outer diameter (mm).
        d_i       : Internal diameter of finished cup (mm).

    Returns:
        List of matplotlib Figure objects (one per stage).
    """
    figures: List[plt.Figure] = []

    # Blank
    figures.append(render_blank(blank_res, t))

    # Each pass
    for pd in seq_res.passes:
        figures.append(render_pass(pd, t, d_f=pd.flange_diameter, d_i=d_i))

    return figures


def render_overview(
    blank_res: BlankResult,
    seq_res: PassSequenceResult,
    t: float,
    d_f: float,
) -> plt.Figure:
    """
    Render a compact overview figure showing all stages side by side.

    Useful as a summary thumbnail. Each stage occupies one subplot column.

    Args:
        blank_res : BlankResult.
        seq_res   : PassSequenceResult.
        t         : Sheet thickness (mm).
        d_f       : Flange outer diameter (mm).

    Returns:
        matplotlib Figure with all stages in a single row.
    """
    n_stages = 1 + seq_res.n_passes
    fig, axes = plt.subplots(1, n_stages,
                             figsize=(4 * n_stages, 6), dpi=100)
    fig.patch.set_facecolor(_COLOR_BG)

    if n_stages == 1:
        axes = [axes]

    def _style(ax):
        ax.set_facecolor(_COLOR_BG)
        ax.set_aspect("equal")
        ax.grid(False)
        for s in ax.spines.values():
            s.set_visible(False)
        ax.tick_params(left=False, bottom=False,
                       labelleft=False, labelbottom=False)

    # --- Blank ---
    ax = axes[0]
    _style(ax)
    d = blank_res.d_blank_final
    r = d / 2.0
    px, py = _blank_fill_polygon(d, t)
    ax.fill(px, py, color=_COLOR_FILL, alpha=0.75)
    for xs, ys in _blank_profile(d, t):
        ax.plot(xs, ys, color=_COLOR_CONTOUR, lw=1.2)
    ax.axvline(x=0, color=_COLOR_AXIS, lw=0.8, linestyle="--")
    ax.set_title("Blank", fontsize=9, fontweight="bold")
    ax.set_xlim(-r * 0.1, r * 1.2)
    ax.set_ylim(-t * 5, t * 8)

    # --- Passes ---
    for i, pd in enumerate(seq_res.passes):
        ax = axes[i + 1]
        _style(ax)
        flange = pd.flange_diameter
        r_i, r_o = _cup_radii(pd.d_after, t)
        r_f = flange / 2.0
        max_r = max(r_f, r_o)
        H = pd.height

        px, py = _cup_fill_polygon(pd, t, flange)
        ax.fill(px, py, color=_COLOR_FILL, alpha=0.75)
        for xs, ys in _cup_profile(pd, t, flange):
            ax.plot(xs, ys, color=_COLOR_CONTOUR, lw=1.2)
        ax.axvline(x=0, color=_COLOR_AXIS, lw=0.8, linestyle="--")

        lbl = f"Passe {pd.pass_number}"
        if pd.is_final:
            lbl += "\n(Final)"
        ax.set_title(lbl, fontsize=9, fontweight="bold")
        ax.set_xlim(-max_r * 0.1, max_r * 1.3)
        ax.set_ylim(-t * 8, H * 1.25)

    fig.suptitle("Sequência de Repuxo Cilíndrico", fontsize=11,
                 fontweight="bold", y=1.01)
    fig.tight_layout()
    return fig
