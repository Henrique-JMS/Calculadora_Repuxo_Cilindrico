"""
blank_calculator.py
===================
Blank diameter calculation for cylindrical deep drawing with flange.

The fundamental principle is conservation of surface area: since sheet
thickness changes negligibly during drawing (< 5%), the surface area of
the flat circular blank equals the total surface area of the finished part.

Geometry considered (per PRD §6.1):
    - Flat bottom (circular disk minus punch-radius toroid footprint)
    - Quarter-toroid fillet: punch radius r_punch (bottom → wall transition)
    - Straight cylindrical wall (height H)
    - Flat annular flange (outer diameter d_f, inner diameter d_e = d_i + 2t)

All dimensions in mm. All areas in mm².

References:
    - Kalpakjian & Schmid — Manufacturing Engineering and Technology, 7th ed.
      Table 16.2 — Blank-diameter formulas for common drawn shapes.
    - Marciniak, Duncan, Hu — Mechanics of Sheet Metal Forming, 2nd ed., §7.2.
    - Schuler — Metal Forming Handbook, Springer 1998, pp. 218–220.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from constants import DEFAULT_TRIM_ALLOWANCE, T_D_RATIO_GREEN, T_D_RATIO_YELLOW


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------

@dataclass
class BlankResult:
    """
    Output of the blank diameter calculation.

    Attributes:
        d_blank_theoretical : Blank diameter from pure surface-area formula (mm).
        d_blank_final       : Blank diameter after adding trim allowance (mm).
        trim_allowance_mm   : Trim margin added to the theoretical blank (mm).
        trim_fraction       : Trim allowance as a fraction of d_blank_theoretical.
        area_bottom         : Surface area of the flat bottom (mm²).
        area_fillet         : Surface area of the punch-radius quarter-toroid (mm²).
        area_wall           : Surface area of the cylindrical wall (mm²).
        area_flange         : Surface area of the annular flange (mm²).
        area_total_part     : Total surface area of the finished part (mm²).
        area_blank          : Surface area of the final blank (mm²).
        t_D_ratio_pct       : t / d_blank_final × 100  (severity indicator, %).
        severity            : "green" | "yellow" | "red"  (t/D severity band).
    """
    d_blank_theoretical: float
    d_blank_final: float
    trim_allowance_mm: float
    trim_fraction: float

    area_bottom: float
    area_fillet: float
    area_wall: float
    area_flange: float
    area_total_part: float
    area_blank: float

    t_D_ratio_pct: float
    severity: str


# ---------------------------------------------------------------------------
# Area helpers (private)
# ---------------------------------------------------------------------------

def _area_flat_bottom(d_i: float, r_punch: float) -> float:
    """
    Surface area of the flat circular bottom.

    The flat region ends where the quarter-toroid begins, so its
    effective diameter is (d_i - 2*r_punch).

    Formula: A = π/4 * (d_i - 2*r_punch)²

    Args:
        d_i     : Internal diameter of the cup (mm).
        r_punch : Punch corner radius (mm).

    Returns:
        Area in mm². Returns 0 if d_i <= 2*r_punch (no flat bottom).
    """
    d_flat = d_i - 2.0 * r_punch
    if d_flat <= 0.0:
        return 0.0
    return math.pi / 4.0 * d_flat ** 2


def _area_punch_fillet(d_i: float, r_punch: float) -> float:
    """
    Surface area of the quarter-toroid (punch corner radius region).

    The quarter-toroid connects the flat bottom to the cylindrical wall.
    Its centroid radius is (d_i/2 - r_punch), and its meridional arc
    length is π*r_punch/2.

    Formula: A = π²/2 * r_punch * (d_i - 2*r_punch) + 2*π*r_punch²

    Derivation (surface of revolution of a quarter-circle arc):
        A = 2π * R_centroid * arc_length
          = 2π * (d_i/2 - r_punch) * (π*r_punch/2)  +  2π*r_punch²
        where the second term accounts for the toroid's inner edge.

    Args:
        d_i     : Internal diameter of the cup (mm).
        r_punch : Punch corner radius (mm).

    Returns:
        Area in mm².
    """
    return (math.pi**2 / 2.0) * r_punch * (d_i - 2.0 * r_punch) + 2.0 * math.pi * r_punch**2


def _area_cylindrical_wall(d_i: float, H: float) -> float:
    """
    Surface area of the straight cylindrical wall.

    Formula: A = π * d_i * H

    Args:
        d_i : Internal diameter (mm).
        H   : Wall height (mm).

    Returns:
        Area in mm².
    """
    return math.pi * d_i * H


def _area_annular_flange(d_f: float, d_i: float, t: float) -> float:
    """
    Surface area of the flat annular flange.

    The flange extends from the outer wall edge (d_e = d_i + 2t) to the
    flange outer diameter d_f.

    Formula: A = π/4 * (d_f² - d_e²)   where d_e = d_i + 2t

    Args:
        d_f : Flange outer diameter (mm).
        d_i : Internal diameter of the cup (mm).
        t   : Sheet thickness (mm).

    Returns:
        Area in mm². Returns 0 if d_f <= d_e.
    """
    d_e = d_i + 2.0 * t       # outer diameter of the cylindrical wall
    if d_f <= d_e:
        return 0.0
    return math.pi / 4.0 * (d_f**2 - d_e**2)


def _severity_band(t_D_pct: float) -> str:
    """Map t/D percentage to a severity label."""
    if t_D_pct >= T_D_RATIO_GREEN:
        return "green"
    if t_D_pct >= T_D_RATIO_YELLOW:
        return "yellow"
    return "red"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_blank(
    d_i: float,
    H: float,
    d_f: float,
    t: float,
    r_punch: float,
    trim_fraction: float = DEFAULT_TRIM_ALLOWANCE,
) -> BlankResult:
    """
    Calculate the blank diameter for a flanged cylindrical cup.

    Method: conservation of surface area.
        A_blank = A_bottom + A_fillet + A_wall + A_flange

    Trim allowance accounts for earing (edge irregularity after drawing):
        D_blank_final = D_blank_theoretical * (1 + trim_fraction)

    Args:
        d_i           : Internal diameter of finished cup (mm). Must be > 0.
        H             : Wall height of finished cup (mm). Must be > 0.
        d_f           : Flange outer diameter (mm). Must be > d_i + 2t.
        t             : Sheet thickness (mm). Must be > 0.
        r_punch       : Punch corner radius (mm). Must be >= 0.
        trim_fraction : Trim allowance as decimal fraction of D_blank
                        (e.g. 0.03 = 3%). Default: 0.03.

    Returns:
        BlankResult dataclass with all intermediate areas and final diameter.

    Raises:
        ValueError: If any input is physically invalid (not expected in normal
                    flow — validators.py should catch these first).
    """
    if d_i <= 0:
        raise ValueError(f"d_i must be > 0. Got {d_i}.")
    if H <= 0:
        raise ValueError(f"H must be > 0. Got {H}.")
    if t <= 0:
        raise ValueError(f"t must be > 0. Got {t}.")
    if r_punch < 0:
        raise ValueError(f"r_punch must be >= 0. Got {r_punch}.")
    if trim_fraction < 0:
        raise ValueError(f"trim_fraction must be >= 0. Got {trim_fraction}.")

    # Clamp r_punch if it would eliminate the entire bottom
    # (geometrically: r_punch < d_i/2 is required for a flat bottom to exist)
    r_punch_eff = min(r_punch, d_i / 2.0 - 1e-9)

    # ---- Surface area breakdown -------------------------------------------
    A_bottom = _area_flat_bottom(d_i, r_punch_eff)
    A_fillet = _area_punch_fillet(d_i, r_punch_eff)
    A_wall   = _area_cylindrical_wall(d_i, H)
    A_flange = _area_annular_flange(d_f, d_i, t)

    A_total = A_bottom + A_fillet + A_wall + A_flange

    # ---- Theoretical blank diameter (from A_blank = π/4 * D²) -----------
    D_theoretical = math.sqrt(4.0 * A_total / math.pi)

    # ---- Trim allowance ---------------------------------------------------
    trim_mm = D_theoretical * trim_fraction
    D_final = D_theoretical + trim_mm

    # ---- Severity indicator -----------------------------------------------
    t_D_pct = (t / D_final) * 100.0
    severity = _severity_band(t_D_pct)

    return BlankResult(
        d_blank_theoretical = round(D_theoretical, 4),
        d_blank_final       = round(D_final, 4),
        trim_allowance_mm   = round(trim_mm, 4),
        trim_fraction       = trim_fraction,
        area_bottom         = round(A_bottom, 4),
        area_fillet         = round(A_fillet, 4),
        area_wall           = round(A_wall, 4),
        area_flange         = round(A_flange, 4),
        area_total_part     = round(A_total, 4),
        area_blank          = round(math.pi / 4.0 * D_final**2, 4),
        t_D_ratio_pct       = round(t_D_pct, 4),
        severity            = severity,
    )
