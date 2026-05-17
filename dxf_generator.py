"""
dxf_generator.py
================
Generates DXF cross-section drawings for each stage of the cylindrical
deep drawing process (blank → intermediate passes → final flanged cup).

Each stage is drawn as a right-half axisymmetric cross-section profile,
placed side-by-side in a single DXF model space.

Coordinate convention (per stage, local):
    - Origin at the centre of the cup's inner bottom surface
    - x : radial direction (0 = symmetry axis, positive = outward)
    - y : axial direction (0 = inner bottom, positive = upward)
    - y = -t : outer bottom surface

Profile construction:
    Inner surface: flat bottom → punch fillet (CCW arc) → cylindrical wall → flange top
    Outer surface: flange edge → die fillet (CCW arc) → outer wall → outer punch fillet → outer bottom

Layers:
    CONTORNO  (white / 7)  – profile contour lines
    EIXO      (red   / 1)  – symmetry axis (centre line)
    COTA      (yellow/ 2)  – dimension annotations
    LEGENDA   (cyan  / 4)  – text labels and stage info
    HATCH     (gray  / 8)  – section hatch (optional)

References:
    - ezdxf documentation: https://ezdxf.readthedocs.io
    - PRD §7 — Geração de Arquivos DXF
"""

from __future__ import annotations

import io
import math
from typing import List, Optional

import ezdxf
from ezdxf.enums import TextEntityAlignment

from blank_calculator import BlankResult
from pass_sequence import PassSequenceResult, PassData

# ---------------------------------------------------------------------------
# Layer configuration
# ---------------------------------------------------------------------------

_LAYERS = {
    "CONTORNO": 7,   # white
    "EIXO":     1,   # red
    "COTA":     2,   # yellow
    "LEGENDA":  4,   # cyan
    "HATCH":    8,   # gray
}

_STAGE_GAP     = 45.0    # horizontal gap between stages (mm)
_TEXT_H_LARGE  = 5.0     # large label text height
_TEXT_H_MEDIUM = 3.5     # medium annotation text height
_TEXT_H_SMALL  = 2.8     # small info text height
_AXIS_MARGIN   = 12.0    # axis line extension beyond profile (mm)
_DIM_OFFSET    = 12.0    # dimension line offset from profile edge (mm)
_LEGEND_OFFSET = 20.0    # legend box offset below profile (mm)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _setup_doc(doc: ezdxf.document.Drawing) -> None:
    """Add layers to DXF document."""
    for name, color in _LAYERS.items():
        layer = doc.layers.add(name)
        layer.color = color


def _ln(msp, p1: tuple, p2: tuple, layer: str = "CONTORNO") -> None:
    """Shorthand: add a LINE entity."""
    msp.add_line(p1, p2, dxfattribs={"layer": layer})


def _arc(msp, cx: float, cy: float, r: float,
         start: float, end: float, layer: str = "CONTORNO") -> None:
    """
    Shorthand: add an ARC entity (ezdxf draws CCW from start to end).

    Args:
        cx, cy : arc centre
        r      : radius
        start  : start angle in degrees (CCW convention)
        end    : end angle in degrees
        layer  : target DXF layer
    """
    msp.add_arc(center=(cx, cy), radius=r,
                start_angle=start, end_angle=end,
                dxfattribs={"layer": layer})


def _txt(msp, text: str, x: float, y: float,
         height: float = _TEXT_H_MEDIUM, layer: str = "LEGENDA",
         align: TextEntityAlignment = TextEntityAlignment.MIDDLE_CENTER) -> None:
    """Shorthand: add a TEXT entity, centre-aligned by default."""
    msp.add_text(text, dxfattribs={"layer": layer, "height": height}
                 ).set_placement((x, y), align=align)


def _cup_radii(d_after: float, t: float) -> tuple[float, float]:
    """
    Derive inner and outer radii from the neutral (mid-plane) diameter.

    In pass_sequence, d_after = neutral diameter = d_i + t.
        r_inner = d_after/2 - t/2 = d_i/2
        r_outer = d_after/2 + t/2 = d_i/2 + t
    """
    r_neutral = d_after / 2.0
    return r_neutral - t / 2.0, r_neutral + t / 2.0


# ---------------------------------------------------------------------------
# Blank stage
# ---------------------------------------------------------------------------

def _draw_blank(msp, x0: float, d_blank: float, t: float) -> float:
    """
    Draw the blank (flat disk) as a right-half cross-section rectangle.

    The blank is shown as a thin horizontal rectangle:
        - bottom edge at y = 0
        - top edge at y = t
        - left edge at x = x0 (symmetry axis)
        - right edge at x = x0 + d_blank/2

    Args:
        msp     : modelspace handle
        x0      : x-coordinate of the symmetry axis
        d_blank : blank diameter (mm)
        t       : sheet thickness (mm)

    Returns:
        Stage width (= d_blank/2 + margin used for next offset calculation).
    """
    r = d_blank / 2.0
    # Profile rectangle
    _ln(msp, (x0,     0), (x0 + r, 0))           # bottom edge
    _ln(msp, (x0 + r, 0), (x0 + r, t))           # outer edge
    _ln(msp, (x0 + r, t), (x0,     t))           # top edge
    # Left edge (axis boundary, drawn on CONTORNO but axis line added separately)
    _ln(msp, (x0, 0), (x0, t))

    # Symmetry axis
    _ln(msp, (x0, -_AXIS_MARGIN), (x0, t + _AXIS_MARGIN), layer="EIXO")

    # --- Diameter dimension ---
    dim_y = t + _DIM_OFFSET
    _ln(msp, (x0, dim_y), (x0 + r, dim_y), layer="COTA")
    # Extension lines
    _ln(msp, (x0,     t), (x0,     dim_y + 2), layer="COTA")
    _ln(msp, (x0 + r, t), (x0 + r, dim_y + 2), layer="COTA")
    _txt(msp, f"\u00d8 {d_blank:.1f}", x0 + r / 2, dim_y + 2.5,
         height=_TEXT_H_MEDIUM, layer="COTA")

    # Thickness callout
    _txt(msp, f"t = {t:.2f}", x0 + r + 6, t / 2,
         height=_TEXT_H_SMALL, layer="COTA",
         align=TextEntityAlignment.MIDDLE_LEFT)

    # Stage title below
    _txt(msp, "BLANK",
         x0 + r / 2, -_LEGEND_OFFSET, height=_TEXT_H_LARGE)
    _txt(msp, f"\u00d8 {d_blank:.1f} \u00d7 {t:.2f} mm",
         x0 + r / 2, -_LEGEND_OFFSET - 7, height=_TEXT_H_MEDIUM)

    return r


# ---------------------------------------------------------------------------
# Cup stage (intermediate or final)
# ---------------------------------------------------------------------------

def _draw_cup(msp, x0: float, pd: PassData, t: float,
              d_f: Optional[float] = None) -> float:
    """
    Draw one cup pass as a right-half axisymmetric cross-section.

    Args:
        msp  : modelspace handle
        x0   : x-coordinate of the symmetry axis for this stage
        pd   : PassData for this pass
        t    : sheet thickness (mm)
        d_f  : flange outer diameter (mm); None for intermediate passes

    Returns:
        Stage width (max radial extent from axis).
    """
    r_i, r_o = _cup_radii(pd.d_after, t)
    H    = pd.height
    r_p  = pd.r_punch
    r_m  = pd.r_die
    r_f  = d_f / 2.0 if d_f is not None else None

    # Clamp punch radius: r_p must leave a flat bottom (r_p < r_i)
    r_p = min(r_p, r_i * 0.99)

    # ------------------------------------------------------------------ #
    # INNER SURFACE (left to right, bottom to top)                        #
    # ------------------------------------------------------------------ #

    # 1. Flat inner bottom (y = 0, from axis to start of punch fillet)
    _ln(msp, (x0, 0), (x0 + r_i - r_p, 0))

    # 2. Inner punch fillet (CCW 270° → 360°)
    #    centre: (x0 + r_i - r_p,  r_p)
    _arc(msp, x0 + r_i - r_p, r_p, r_p, 270, 360)

    # 3. Inner wall (vertical, upward)
    _ln(msp, (x0 + r_i, r_p), (x0 + r_i, H))

    # 4a. Final pass: flange top surface
    if r_f is not None:
        _ln(msp, (x0 + r_i, H), (x0 + r_f, H))
    # 4b. Intermediate pass: rim top edge
    else:
        _ln(msp, (x0 + r_i, H), (x0 + r_o, H))

    # ------------------------------------------------------------------ #
    # OUTER SURFACE (top to bottom, closing the profile)                  #
    # ------------------------------------------------------------------ #

    if r_f is not None:
        # 5. Outer flange edge (vertical, downward)
        _ln(msp, (x0 + r_f, H), (x0 + r_f, H - t))

        # 6. Flange bottom (inward to die fillet tangent point)
        die_tp_x = r_o - r_m          # tangent point x (relative to axis)
        _ln(msp, (x0 + r_f, H - t), (x0 + die_tp_x, H - t))

        # 7. Die fillet (outer wall → flange bottom)
        #    centre: (x0 + r_o - r_m, H - t - r_m)
        #    CCW 0° → 90°: from (r_o, H-t-r_m) on wall to (r_o-r_m, H-t) on flange
        _arc(msp, x0 + r_o - r_m, H - t - r_m, r_m, 0, 90)

        # 8. Outer wall (downward from die fillet to outer punch fillet)
        _ln(msp, (x0 + r_o, H - t - r_m), (x0 + r_o, r_p))

    else:
        # Intermediate: outer wall from rim down to outer punch fillet
        _ln(msp, (x0 + r_o, H), (x0 + r_o, r_p))

    # 9. Outer punch fillet (CCW 270° → 360°)
    #    same centre as inner, radius = r_p + t
    _arc(msp, x0 + r_i - r_p, r_p, r_p + t, 270, 360)

    # 10. Outer bottom (inward to axis)
    _ln(msp, (x0 + r_i - r_p, -t), (x0, -t))

    # 11. Axis boundary (close profile on left)
    _ln(msp, (x0, -t), (x0, 0))

    # ------------------------------------------------------------------ #
    # SYMMETRY AXIS                                                        #
    # ------------------------------------------------------------------ #
    _ln(msp, (x0, -t - _AXIS_MARGIN), (x0, H + _AXIS_MARGIN), layer="EIXO")

    # ------------------------------------------------------------------ #
    # DIMENSIONS                                                           #
    # ------------------------------------------------------------------ #
    max_r = r_f if r_f is not None else r_o

    # Inner diameter (horizontal, below the cup)
    dim_y_d = -t - _DIM_OFFSET
    _ln(msp, (x0, dim_y_d), (x0 + r_i, dim_y_d), layer="COTA")
    _ln(msp, (x0,     -t), (x0,     dim_y_d - 2), layer="COTA")
    _ln(msp, (x0 + r_i, -t), (x0 + r_i, dim_y_d - 2), layer="COTA")
    _txt(msp, f"\u00d8i {r_i * 2:.1f}", x0 + r_i / 2, dim_y_d - 3.5,
         height=_TEXT_H_SMALL, layer="COTA")

    # Flange diameter (if present)
    if r_f is not None:
        dim_y_f = -t - _DIM_OFFSET - 9
        _ln(msp, (x0, dim_y_f), (x0 + r_f, dim_y_f), layer="COTA")
        _ln(msp, (x0 + r_f, H - t), (x0 + r_f, dim_y_f - 2), layer="COTA")
        _txt(msp, f"\u00d8f {r_f * 2:.1f}", x0 + r_f / 2, dim_y_f - 3.5,
             height=_TEXT_H_SMALL, layer="COTA")

    # Height dimension (vertical, right of profile)
    dim_x_h = x0 + max_r + _DIM_OFFSET
    _ln(msp, (dim_x_h, 0), (dim_x_h, H), layer="COTA")
    _ln(msp, (x0 + r_i, 0), (dim_x_h + 2, 0), layer="COTA")
    _ln(msp, (x0 + max_r, H), (dim_x_h + 2, H), layer="COTA")
    _txt(msp, f"H {H:.1f}", dim_x_h + 4, H / 2,
         height=_TEXT_H_SMALL, layer="COTA",
         align=TextEntityAlignment.MIDDLE_LEFT)

    # ------------------------------------------------------------------ #
    # STAGE LEGEND (below)                                                 #
    # ------------------------------------------------------------------ #
    is_final = pd.is_final
    legend_label = f"PASSE {pd.pass_number}" + (" (FINAL)" if is_final else "")
    legend_cx = x0 + max_r / 2

    _txt(msp, legend_label,
         legend_cx, -t - _LEGEND_OFFSET, height=_TEXT_H_LARGE)
    _txt(msp, f"DR = {pd.drawing_ratio:.3f}   m = {pd.drawing_coeff:.3f}",
         legend_cx, -t - _LEGEND_OFFSET - 7, height=_TEXT_H_MEDIUM)
    _txt(msp, f"\u00d8 {pd.d_after * 2:.1f} \u00d7 H {H:.1f} mm",
         legend_cx, -t - _LEGEND_OFFSET - 13, height=_TEXT_H_MEDIUM)

    return max_r


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_dxf(
    blank_res: BlankResult,
    seq_res: PassSequenceResult,
    t: float,
    d_f: float,
) -> ezdxf.document.Drawing:
    """
    Generate a DXF document with all drawing stages laid out side by side.

    Layout (left to right in model space):
        [ BLANK ] | [ PASS 1 ] | [ PASS 2 ] | ... | [ PASS N (FINAL) ]

    Args:
        blank_res : Result of blank_calculator.compute_blank().
        seq_res   : Result of pass_sequence.compute_pass_sequence().
        t         : Sheet thickness (mm).
        d_f       : Flange outer diameter of the finished part (mm).

    Returns:
        ezdxf Drawing object (can be saved or serialised to bytes).
    """
    doc = ezdxf.new("R2010")
    doc.header["$INSUNITS"] = 4   # millimetres
    doc.header["$LUNITS"]   = 2   # decimal
    _setup_doc(doc)
    msp = doc.modelspace()

    x_cursor = 0.0

    # ---- Blank stage -------------------------------------------------------
    stage_w = _draw_blank(msp, x_cursor, blank_res.d_blank_final, t)
    x_cursor += stage_w + _STAGE_GAP

    # ---- Cup stages (intermediate + final) ---------------------------------
    passes = seq_res.passes
    for idx, pd in enumerate(passes):
        is_last = pd.is_final
        flange = d_f if is_last else None
        stage_w = _draw_cup(msp, x_cursor, pd, t, d_f=flange)
        x_cursor += stage_w + _STAGE_GAP

    # ---- Global title block ------------------------------------------------
    title_x = x_cursor / 2.0
    title_y = -60.0
    _txt(msp, "SEQUÊNCIA DE REPUXO CILÍNDRICO",
         title_x, title_y, height=7.0)
    _txt(msp, f"N° de passes: {seq_res.n_passes}   |   "
              f"Blank: \u00d8 {blank_res.d_blank_final:.1f} mm   |   "
              f"t = {t:.2f} mm",
         title_x, title_y - 10.0, height=_TEXT_H_MEDIUM)

    return doc


def generate_dxf_bytes(
    blank_res: BlankResult,
    seq_res: PassSequenceResult,
    t: float,
    d_f: float,
) -> bytes:
    """
    Generate the DXF document and return it as a bytes object.

    Suitable for Streamlit's st.download_button().

    Args:
        blank_res : BlankResult from blank_calculator.
        seq_res   : PassSequenceResult from pass_sequence.
        t         : Sheet thickness (mm).
        d_f       : Flange outer diameter (mm).

    Returns:
        DXF file content as bytes (UTF-8 encoded).
    """
    doc = generate_dxf(blank_res, seq_res, t, d_f)
    stream = io.StringIO()
    doc.write(stream)
    return stream.getvalue().encode("utf-8")
