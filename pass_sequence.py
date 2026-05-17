"""
pass_sequence.py
================
Determines the number of drawing passes and calculates the intermediate
dimensions (diameter and height) for each pass of a cylindrical deep drawing
operation with flange.

Algorithm (per PRD §6.2 – §6.4):
    1. From the blank diameter D_b and the target neutral diameter d_target,
       compute the total drawing ratio DR_total = D_b / d_target.
    2. If DR_total <= 1/m1_lim, a single pass suffices.
    3. Otherwise, iterate: assign d_1 = m1_lim * D_b, then
       d_n = mn_lim * d_{n-1}, until d_n <= d_target.
    4. The diameters are then redistributed uniformly so that d_N == d_target
       exactly, preserving the relative severity distribution.
    5. Heights are derived from surface-area conservation at each step.

All dimensions in mm.

References:
    - Kalpakjian & Schmid — Manufacturing Engineering and Technology, 7th ed.,
      §16.5, Table 16.3.
    - Marciniak, Duncan, Hu — Mechanics of Sheet Metal Forming, 2nd ed., §7.3.
    - Schuler — Metal Forming Handbook, Springer 1998, pp. 222–226.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List

from constants import (
    INTERMEDIATE_DIE_RADIUS_FACTOR,
    DR_GREEN,
    DR_YELLOW,
)


# ---------------------------------------------------------------------------
# Result containers
# ---------------------------------------------------------------------------

@dataclass
class PassData:
    """
    Dimensions and drawing parameters for a single pass.

    Attributes:
        pass_number      : 1-based index of this pass.
        d_before         : Diameter of the blank/semi-product entering this
                           pass (mm). Equal to D_blank for pass 1.
        d_after          : Diameter of the semi-product after this pass (mm).
        d_neutral_after  : Mid-plane (neutral) diameter after pass = d_after + t (mm).
        height           : Accumulated cup height after this pass (mm).
        drawing_coeff    : m = d_after / d_before  (dimensionless).
        drawing_ratio    : DR = d_before / d_after = 1/m  (dimensionless).
        reduction_pct    : Percentage diameter reduction = (1 - m) * 100 (%).
        r_die            : Die corner radius used for this pass (mm).
        severity         : "green" | "yellow" | "red"  (DR severity band).
        is_final         : True for the last pass.
    """
    pass_number:     int
    d_before:        float
    d_after:         float
    d_neutral_after: float
    height:          float
    drawing_coeff:   float
    drawing_ratio:   float
    reduction_pct:   float
    r_die:           float
    r_punch:         float
    severity:        str
    is_final:        bool = False


@dataclass
class PassSequenceResult:
    """
    Full output of the pass-sequence computation.

    Attributes:
        n_passes          : Total number of drawing passes.
        d_blank           : Final blank diameter (with trim, mm).
        d_target          : Target neutral diameter of finished part (mm).
        total_drawing_ratio : DR_total = d_blank / d_target.
        passes            : Ordered list of PassData (1 per pass).
    """
    n_passes:            int
    d_blank:             float
    d_target:            float
    total_drawing_ratio: float
    passes:              List[PassData] = field(default_factory=list)

    @property
    def first_pass(self) -> PassData:
        return self.passes[0]

    @property
    def last_pass(self) -> PassData:
        return self.passes[-1]


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _severity_band(dr: float) -> str:
    if dr <= DR_GREEN:
        return "green"
    if dr <= DR_YELLOW:
        return "yellow"
    return "red"


def _height_from_area(D_blank: float, d_cup: float, r_punch: float) -> float:
    """
    Estimate cup height at a given intermediate diameter using surface-area
    conservation (no flange assumed for intermediate passes).

    The height is derived by equating the blank area to the cup area:
        π/4 * D_blank² = π/4 * (d_cup - 2r_punch)²   [flat bottom]
                        + π²/2 * r_punch * (d_cup - 2r_punch) + 2π*r_punch²  [fillet]
                        + π * d_cup * H_wall  [wall]

    Solving for H_wall:
        H_wall = [D_blank²/4 - d_cup²/4 + r_punch*(d_cup/2 - r_punch/2) - r_punch²/2
                  ... (simplified for intermediate passes without flange)] / d_cup

    For simplicity we use the classical approximation (no fillet correction)
    and add a small fillet correction term. The final pass height is always
    taken from the user input H directly.

    Args:
        D_blank : Blank diameter (mm).
        d_cup   : Cup outer diameter at this pass (mm). Using d_after.
        r_punch : Punch radius for this pass (mm).

    Returns:
        Estimated wall height (mm). Always >= 0.
    """
    # Classical formula: D² = d² + 4dH  →  H = (D² - d²) / (4d)
    # (valid for no-fillet, no-flange cup; good enough for intermediate passes)
    H_approx = (D_blank**2 - d_cup**2) / (4.0 * d_cup)

    # Fillet correction: subtract the height contribution of the punch radius
    # (the fillet region replaces the bottom of the wall)
    if r_punch > 0:
        H_approx -= r_punch * (1.0 - math.pi / 4.0)

    return max(H_approx, 0.0)


def _distribute_diameters(
    D_blank: float,
    d_target: float,
    n: int,
    m1_lim: float,
    mn_lim: float,
) -> List[float]:
    """
    Distribute intermediate diameters across n passes so that:
        - d[0] = D_blank (entry to pass 1)
        - d[n] = d_target (exit of last pass)
        - The sequence is geometrically consistent with m1_lim / mn_lim
          severity constraints.

    Strategy:
        1. Compute raw sequence using m1_lim and mn_lim.
        2. Scale all intermediate diameters proportionally so that the
           last element equals d_target exactly.

    This ensures that no individual pass exceeds its m_lim while still
    landing exactly on the required final diameter.

    Args:
        D_blank  : Blank diameter (mm).
        d_target : Target cup neutral diameter (mm).
        n        : Number of passes.
        m1_lim   : 1st-pass drawing coefficient limit.
        mn_lim   : Subsequent-pass drawing coefficient limit.

    Returns:
        List of diameters of length n+1, where index 0 = D_blank,
        index n = d_target, and intermediate values are the semi-product
        diameters after each pass.
    """
    # Step 1 — raw sequence using coefficient limits
    raw = [D_blank]
    for i in range(n):
        m = m1_lim if i == 0 else mn_lim
        raw.append(raw[-1] * m)

    # Step 2 — scale so that raw[-1] == d_target
    # The scale factor is applied to each intermediate diameter (not D_blank).
    raw_final = raw[-1]
    if abs(raw_final - d_target) < 1e-9:
        return raw  # already exact

    # Linear interpolation in log space to preserve shape of reduction curve
    scale = math.log(d_target / D_blank) / math.log(raw_final / D_blank)
    distributed = [D_blank]
    for i in range(1, n + 1):
        # Interpolate in log space: d_i = D_blank * (raw_i/D_blank)^scale
        ratio = raw[i] / D_blank
        d_i = D_blank * (ratio ** scale)
        distributed.append(d_i)

    # Force the last element to be exactly d_target (avoid fp drift)
    distributed[-1] = d_target
    return distributed


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_pass_sequence(
    d_blank: float,
    d_i: float,
    H: float,
    t: float,
    r_die_final: float,
    r_punch_final: float,
    m1_lim: float,
    mn_lim: float,
) -> PassSequenceResult:
    """
    Compute the complete drawing pass sequence for a flanged cylindrical cup.

    Args:
        d_blank       : Final blank diameter (with trim allowance), mm.
        d_i           : Internal diameter of the finished cup (mm).
        H             : Wall height of the finished cup (mm).
        t             : Sheet thickness (mm).
        r_die_final   : Die corner radius for the final pass (mm).
        r_punch_final : Punch corner radius for the final pass (mm).
        m1_lim        : Limiting drawing coefficient for the 1st pass.
        mn_lim        : Limiting drawing coefficient for subsequent passes.

    Returns:
        PassSequenceResult with all pass data.

    Raises:
        ValueError: If inputs are inconsistent.
    """
    if d_blank <= 0:
        raise ValueError(f"d_blank must be > 0. Got {d_blank}.")
    if d_i <= 0:
        raise ValueError(f"d_i must be > 0. Got {d_i}.")
    if t <= 0:
        raise ValueError(f"t must be > 0. Got {t}.")

    # Target neutral (mid-plane) diameter of the finished cup wall
    d_target = d_i + t

    DR_total = d_blank / d_target

    # ------------------------------------------------------------------ #
    # Step 1 — determine number of passes                                 #
    # ------------------------------------------------------------------ #
    if DR_total <= (1.0 / m1_lim):
        n_passes = 1
    else:
        # Simulate the sequence with limiting coefficients
        n_passes = 1
        d_sim = d_blank * m1_lim
        while d_sim > d_target:
            d_sim *= mn_lim
            n_passes += 1
            if n_passes > 20:
                # Safety guard; extremely deep draw
                break

    # ------------------------------------------------------------------ #
    # Step 2 — distribute diameters                                       #
    # ------------------------------------------------------------------ #
    diameters = _distribute_diameters(d_blank, d_target, n_passes, m1_lim, mn_lim)

    # ------------------------------------------------------------------ #
    # Step 3 — build PassData for each pass                               #
    # ------------------------------------------------------------------ #
    passes: List[PassData] = []

    for i in range(n_passes):
        d_before = diameters[i]
        d_after  = diameters[i + 1]
        is_final = (i == n_passes - 1)

        m  = d_after / d_before
        dr = d_before / d_after

        # Die radius: use final value for last pass, intermediate factor for others
        if is_final:
            r_die = r_die_final
            r_punch = r_punch_final
        else:
            r_die   = INTERMEDIATE_DIE_RADIUS_FACTOR * t
            r_punch = INTERMEDIATE_DIE_RADIUS_FACTOR * t  # same for intermediates

        # Height: final pass uses user-specified H; intermediates from area formula
        if is_final:
            height = H
        else:
            height = _height_from_area(d_blank, d_after, r_punch)

        passes.append(PassData(
            pass_number      = i + 1,
            d_before         = round(d_before, 4),
            d_after          = round(d_after, 4),
            d_neutral_after  = round(d_after + t, 4),
            height           = round(height, 4),
            drawing_coeff    = round(m, 6),
            drawing_ratio    = round(dr, 6),
            reduction_pct    = round((1.0 - m) * 100.0, 4),
            r_die            = round(r_die, 4),
            r_punch          = round(r_punch, 4),
            severity         = _severity_band(dr),
            is_final         = is_final,
        ))

    return PassSequenceResult(
        n_passes            = n_passes,
        d_blank             = round(d_blank, 4),
        d_target            = round(d_target, 4),
        total_drawing_ratio = round(DR_total, 6),
        passes              = passes,
    )
