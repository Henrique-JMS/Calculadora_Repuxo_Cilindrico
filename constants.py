"""
constants.py
============
Centralized physical constants and empirical coefficients for the
cylindrical drawing calculator.

All values are in SI-compatible units (mm, N, MPa) unless noted.

References:
    - Kalpakjian, S. & Schmid, S.R. — Manufacturing Engineering and Technology, 7th ed.
    - Marciniak, Z., Duncan, J.L., Hu, S.J. — Mechanics of Sheet Metal Forming, 2nd ed.
    - Schuler GmbH — Metal Forming Handbook, Springer, 1998.
"""

import math

# ---------------------------------------------------------------------------
# Geometric / process limits
# ---------------------------------------------------------------------------

# Minimum die radius as a multiple of sheet thickness (hard minimum to avoid fracture)
MIN_DIE_RADIUS_FACTOR: float = 2.0      # r_die >= MIN_DIE_RADIUS_FACTOR * t

# Recommended die radius (soft warning threshold)
RECOMMENDED_DIE_RADIUS_FACTOR: float = 4.0  # r_die >= 4t  (warn if below)

# Minimum punch radius as a multiple of sheet thickness
MIN_PUNCH_RADIUS_FACTOR: float = 2.0    # r_punch >= 2t

# Recommended punch radius (soft warning)
RECOMMENDED_PUNCH_RADIUS_FACTOR: float = 3.0  # r_punch >= 3t

# ---------------------------------------------------------------------------
# Blank holder (prensa-chapas)
# ---------------------------------------------------------------------------

# Practical blank holder pressure coefficient (Kawai/industry rule)
# p_bh = BH_PRESSURE_COEFF * Ys
BH_PRESSURE_COEFF: float = 0.015

# Severity bands for t/D ratio (%) — (green: > HIGH, yellow: LOW–HIGH, red: < LOW)
T_D_RATIO_GREEN: float = 1.5    # %
T_D_RATIO_YELLOW: float = 0.5   # %

# ---------------------------------------------------------------------------
# Drawing ratio / coefficient limits
# ---------------------------------------------------------------------------

# Default limiting drawing ratios per pass if material doesn't override.
# These are conservative values applicable to low-carbon steel DC01/DC04.
DEFAULT_M1_LIM: float = 0.50   # 1st pass drawing coefficient limit
DEFAULT_MN_LIM: float = 0.75   # Subsequent passes drawing coefficient limit

# Severity bands for drawing ratio DR = 1/m
DR_GREEN: float  = 1.8
DR_YELLOW: float = 2.0

# ---------------------------------------------------------------------------
# Force calculation
# ---------------------------------------------------------------------------

# Siebel correction constant in punch force formula
# F_punch = pi * d * t * UTS * (DR - SIEBEL_CORRECTION)
SIEBEL_CORRECTION: float = 0.7

# Extraction force as fraction of punch force
EXTRACTION_FORCE_FACTOR: float = 0.08   # F_ext = EXTRACTION_FORCE_FACTOR * F_punch

# Default press capacity safety factor
DEFAULT_SAFETY_FACTOR: float = 1.25

# Mechanical efficiency of the press mechanism.
# Used to compute input energy from useful work: W_in = W_useful / η
PRESS_EFFICIENCY: float = 0.65

# ---------------------------------------------------------------------------
# Trim allowance (margem de apara)
# ---------------------------------------------------------------------------

# Default blank trim allowance as fraction of calculated blank diameter
DEFAULT_TRIM_ALLOWANCE: float = 0.03   # 3%
MIN_TRIM_ALLOWANCE: float = 0.00
MAX_TRIM_ALLOWANCE: float = 0.10

# ---------------------------------------------------------------------------
# Punch–die clearance (folga punção-matriz)
# ---------------------------------------------------------------------------

# Clearance per side: c = t + k * sqrt(1000 * t)
# k values by material group:
CLEARANCE_K_STEEL:     float = 0.07
CLEARANCE_K_STAINLESS: float = 0.07
CLEARANCE_K_ALUMINIUM: float = 0.06
CLEARANCE_K_COPPER:    float = 0.06

# ---------------------------------------------------------------------------
# Severity indicator bands — df/d ratio (flange width)
# ---------------------------------------------------------------------------
DF_D_GREEN:  float = 1.5
DF_D_YELLOW: float = 2.0

# ---------------------------------------------------------------------------
# Severity indicator bands — H/d ratio (height/diameter)
# ---------------------------------------------------------------------------
H_D_GREEN:  float = 0.5
H_D_YELLOW: float = 1.0

# ---------------------------------------------------------------------------
# Numerical tolerances
# ---------------------------------------------------------------------------

# Maximum cumulative rounding error allowed on intermediate diameters (mm)
DIAMETER_TOLERANCE_MM: float = 0.01

# Floating-point near-zero threshold
NEAR_ZERO: float = 1e-9
