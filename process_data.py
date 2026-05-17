"""
process_data.py
===============
Calculates all technical production data for each drawing pass:
    - Punch (drawing) force — Siebel formula
    - Blank-holder contact area
    - Blank-holder pressure and force
    - Extraction force
    - Minimum press capacity
    - Energy per cycle
    - Severity indicators (t/D, DR, df/d, H/d) with RAG status

All forces in Newtons (N), converted to kN for display.
All pressures in MPa.
All areas in mm².

References:
    - Kalpakjian & Schmid — Manufacturing Engineering and Technology, 7th ed.,
      Eq. 16.4 (punch force), §16.3 (blank holder).
    - Schuler — Metal Forming Handbook, Springer 1998, pp. 229–234.
    - PRD §6.5 — Dados Técnicos de Produção.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List

from constants import (
    SIEBEL_CORRECTION,
    EXTRACTION_FORCE_FACTOR,
    DEFAULT_SAFETY_FACTOR,
    PRESS_EFFICIENCY,
    T_D_RATIO_GREEN,
    T_D_RATIO_YELLOW,
    DR_GREEN,
    DR_YELLOW,
    DF_D_GREEN,
    DF_D_YELLOW,
    H_D_GREEN,
    H_D_YELLOW,
)
from pass_sequence import PassData


# ---------------------------------------------------------------------------
# Result containers
# ---------------------------------------------------------------------------

@dataclass
class PassForces:
    """
    Technical production data for a single drawing pass.

    Attributes:
        pass_number          : 1-based pass index.
        F_punch_N            : Punch (drawing) force (N).
        F_punch_kN           : Punch force in kN.
        A_blank_holder_mm2   : Blank-holder contact area (mm²).
        p_blank_holder_MPa   : Blank-holder pressure (MPa).
        F_blank_holder_N     : Blank-holder force (N).
        F_blank_holder_kN    : Blank-holder force (kN).
        F_extraction_N       : Extraction force (N).
        F_extraction_kN      : Extraction force (kN).
        F_press_N            : Minimum press capacity (N).
        F_press_kN           : Minimum press capacity (kN).
        F_press_tonf         : Minimum press capacity (metric ton-force).
        energy_J             : Energy per cycle (J).
        drawing_ratio        : DR for this pass (dimensionless).
        drawing_coeff        : m for this pass (dimensionless).
        severity_dr          : "green" | "yellow" | "red"  (DR band).
    """
    pass_number:          int
    F_punch_N:            float
    F_punch_kN:           float
    A_blank_holder_mm2:   float
    p_blank_holder_MPa:   float
    F_blank_holder_N:     float
    F_blank_holder_kN:    float
    F_extraction_N:       float
    F_extraction_kN:      float
    F_press_N:            float
    F_press_kN:           float
    F_press_tonf:         float
    energy_J:             float
    drawing_ratio:        float
    drawing_coeff:        float
    severity_dr:          str


@dataclass
class SeverityIndicators:
    """
    Global severity indicators for the complete process.

    Attributes:
        t_D_ratio_pct    : t / D_blank × 100  (%).
        severity_t_D     : RAG status for t/D.
        DR_first         : Drawing ratio of the first pass.
        severity_DR      : RAG status for DR (worst pass).
        df_d_ratio       : d_f / d_neutral  (flange width indicator).
        severity_df_d    : RAG status for df/d.
        H_d_ratio        : H / d_neutral  (depth indicator).
        severity_H_d     : RAG status for H/d.
        n_passes         : Total number of passes.
    """
    t_D_ratio_pct:  float
    severity_t_D:   str
    DR_first:       float
    severity_DR:    str
    df_d_ratio:     float
    severity_df_d:  str
    H_d_ratio:      float
    severity_H_d:   str
    n_passes:       int


@dataclass
class ProcessDataResult:
    """
    Complete output of the process-data module.

    Attributes:
        passes     : List of per-pass force data (one entry per pass).
        severity   : Global severity indicators.
        peak_press_kN  : Maximum press force across all passes (kN).
        peak_press_tonf: Maximum press force across all passes (ton-force).
    """
    passes:          List[PassForces] = field(default_factory=list)
    severity:        SeverityIndicators = None
    peak_press_kN:   float = 0.0
    peak_press_tonf: float = 0.0


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _rag(value: float, green_threshold: float, yellow_threshold: float,
         higher_is_worse: bool = True) -> str:
    """
    Return "green", "yellow", or "red" based on value and thresholds.

    If higher_is_worse=True (default):
        value <= green  → green
        green < value <= yellow → yellow
        value > yellow  → red
    """
    if higher_is_worse:
        if value <= green_threshold:
            return "green"
        if value <= yellow_threshold:
            return "yellow"
        return "red"
    else:
        # Lower is worse (e.g. t/D ratio — higher is better)
        if value >= green_threshold:
            return "green"
        if value >= yellow_threshold:
            return "yellow"
        return "red"


def _punch_force(d_after: float, t: float, uts: float, dr: float) -> float:
    """
    Punch (drawing) force via Siebel formula.

    F = π · d · t · UTS · (DR - SIEBEL_CORRECTION)

    Args:
        d_after : Cup diameter after this pass (mm). Mid-plane = d_after + t/2
                  but industry convention uses d_after directly.
        t       : Sheet thickness (mm).
        uts     : Ultimate Tensile Strength (MPa).
        dr      : Drawing ratio for this pass (D_before / d_after).

    Returns:
        Force in Newtons (N).
    """
    return math.pi * d_after * t * uts * (dr - SIEBEL_CORRECTION)


def _bh_contact_area(d_before: float, d_after: float, r_die: float) -> float:
    """
    Blank-holder (prensa-chapas) contact area — annular region.

    A_bh = π/4 · [ D_before² - (d_after + 2·r_die)² ]

    The inner boundary of the contact area is the die shoulder
    (d_after + 2*r_die), not d_after itself.

    Returns:
        Area in mm². Returns 0 if d_before is not larger than the inner boundary.
    """
    d_inner = d_after + 2.0 * r_die
    if d_before <= d_inner:
        return 0.0
    return math.pi / 4.0 * (d_before**2 - d_inner**2)


def _bh_pressure(ys: float) -> float:
    """
    Blank-holder pressure via practical rule.

    p_bh = BH_PRESSURE_COEFF · Ys  (MPa)

    Returns:
        Pressure in MPa.
    """
    from constants import BH_PRESSURE_COEFF
    return BH_PRESSURE_COEFF * ys


def _extraction_force(F_punch: float) -> float:
    """Extraction force = EXTRACTION_FORCE_FACTOR × F_punch (N)."""
    return EXTRACTION_FORCE_FACTOR * F_punch


def _press_capacity(F_punch: float, F_bh: float, safety_factor: float) -> float:
    """
    Minimum required press capacity (N).

    F_press = (F_punch + F_bh) × safety_factor
    """
    return (F_punch + F_bh) * safety_factor


def _energy(F_punch: float, height: float) -> float:
    """
    Energy per cycle (J = N·mm / 1000 → convert mm to m).

    W = F_punch × height × efficiency / 1000
    (height in mm → /1000 to convert to m; result in N·m = J)
    """
    return F_punch * height * PRESS_EFFICIENCY / 1000.0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_process_data(
    passes_geom: List[PassData],
    d_blank: float,
    d_f: float,
    H: float,
    t: float,
    uts: float,
    ys: float,
    safety_factor: float = DEFAULT_SAFETY_FACTOR,
) -> ProcessDataResult:
    """
    Compute all technical production data for a complete drawing sequence.

    Args:
        passes_geom    : Output of pass_sequence.compute_pass_sequence().passes.
        d_blank        : Final blank diameter (mm).
        d_f            : Flange outer diameter of finished part (mm).
        H              : Wall height of finished part (mm).
        t              : Sheet thickness (mm).
        uts            : Ultimate Tensile Strength (MPa).
        ys             : Yield Strength (MPa).
        safety_factor  : Press capacity safety factor (default 1.25).

    Returns:
        ProcessDataResult with per-pass forces and global severity indicators.
    """
    pass_forces: List[PassForces] = []

    p_bh = _bh_pressure(ys)

    for pd in passes_geom:
        F_punch = _punch_force(pd.d_after, t, uts, pd.drawing_ratio)
        # Ensure force is positive (if DR < SIEBEL_CORRECTION, clamp to 0)
        F_punch = max(F_punch, 0.0)

        A_bh = _bh_contact_area(pd.d_before, pd.d_after, pd.r_die)
        F_bh = p_bh * A_bh

        F_ext  = _extraction_force(F_punch)
        F_press = _press_capacity(F_punch, F_bh, safety_factor)
        W      = _energy(F_punch, pd.height)

        pass_forces.append(PassForces(
            pass_number          = pd.pass_number,
            F_punch_N            = round(F_punch, 2),
            F_punch_kN           = round(F_punch / 1000.0, 3),
            A_blank_holder_mm2   = round(A_bh, 2),
            p_blank_holder_MPa   = round(p_bh, 4),
            F_blank_holder_N     = round(F_bh, 2),
            F_blank_holder_kN    = round(F_bh / 1000.0, 3),
            F_extraction_N       = round(F_ext, 2),
            F_extraction_kN      = round(F_ext / 1000.0, 3),
            F_press_N            = round(F_press, 2),
            F_press_kN           = round(F_press / 1000.0, 3),
            F_press_tonf         = round(F_press / 9806.65, 4),
            energy_J             = round(W, 4),
            drawing_ratio        = pd.drawing_ratio,
            drawing_coeff        = pd.drawing_coeff,
            severity_dr          = pd.severity,
        ))

    # ---- Global severity indicators ----------------------------------------
    d_neutral = passes_geom[-1].d_after   # neutral diameter of finished cup
    t_D_pct   = (t / d_blank) * 100.0
    DR_first  = passes_geom[0].drawing_ratio
    df_d      = d_f / d_neutral if d_neutral > 0 else 0.0
    H_d       = H / d_neutral if d_neutral > 0 else 0.0

    # worst DR across all passes (highest is most critical)
    worst_DR = max(p.drawing_ratio for p in passes_geom)

    severity = SeverityIndicators(
        t_D_ratio_pct = round(t_D_pct, 3),
        severity_t_D  = _rag(t_D_pct, T_D_RATIO_GREEN, T_D_RATIO_YELLOW,
                              higher_is_worse=False),
        DR_first      = round(DR_first, 4),
        severity_DR   = _rag(worst_DR, DR_GREEN, DR_YELLOW, higher_is_worse=True),
        df_d_ratio    = round(df_d, 4),
        severity_df_d = _rag(df_d, DF_D_GREEN, DF_D_YELLOW, higher_is_worse=True),
        H_d_ratio     = round(H_d, 4),
        severity_H_d  = _rag(H_d, H_D_GREEN, H_D_YELLOW, higher_is_worse=True),
        n_passes      = len(passes_geom),
    )

    peak_N    = max(pf.F_press_N for pf in pass_forces)
    peak_kN   = peak_N / 1000.0
    peak_tonf = peak_N / 9806.65

    return ProcessDataResult(
        passes          = pass_forces,
        severity        = severity,
        peak_press_kN   = round(peak_kN, 3),
        peak_press_tonf = round(peak_tonf, 3),
    )
