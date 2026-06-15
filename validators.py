"""
validators.py
=============
Input validation for the cylindrical drawing calculator.

All validation is non-raising by design — instead, the module returns
structured ValidationResult objects so the UI layer (Streamlit) can
decide how to display errors and warnings without try/except gymnastics.

Validation hierarchy:
    ERROR   — blocks calculation; physically impossible or mathematically
              undefined input (e.g. d_f <= d_i + 2t, t <= 0).
    WARNING — calculation proceeds but user should be aware of a risk
              (e.g. r_die < 4t is allowed but may cause fracture in practice).

Usage:
    from validators import validate_inputs, ValidationResult

    result = validate_inputs(
        d_i=80.0, H=60.0, d_f=120.0, t=1.5,
        r_die=6.0, r_punch=4.5,
        uts=310.0, ys=175.0,
        m1_lim=0.50, mn_lim=0.75,
    )

    if result.has_errors:
        print(result.errors)
    else:
        # proceed with calculation
        ...

References:
    - PRD §5.3 — Validações de Input
    - Kalpakjian, S. & Schmid, S.R. — Manufacturing Engineering and Technology, 7th ed.
    - Marciniak, Z., Duncan, J.L., Hu, S.J. — Mechanics of Sheet Metal Forming, 2nd ed.
    - Schuler GmbH — Metal Forming Handbook, Springer, 1998.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from constants import (
    MIN_DIE_RADIUS_FACTOR,
    MIN_PUNCH_RADIUS_FACTOR,
    RECOMMENDED_DIE_RADIUS_FACTOR,
    RECOMMENDED_PUNCH_RADIUS_FACTOR,
    T_D_RATIO_YELLOW,
    DR_YELLOW,
)


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------

@dataclass
class ValidationResult:
    """
    Container for the outcome of input validation.

    Attributes:
        errors:   List of blocking error messages (str).
        warnings: List of non-blocking warning messages (str).
    """
    errors:   List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        """True if any blocking errors were found."""
        return len(self.errors) > 0

    @property
    def has_warnings(self) -> bool:
        """True if any non-blocking warnings were found."""
        return len(self.warnings) > 0

    @property
    def is_valid(self) -> bool:
        """True if there are no blocking errors (warnings are allowed)."""
        return not self.has_errors

    def add_error(self, msg: str) -> None:
        self.errors.append(msg)

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)

    def __repr__(self) -> str:
        status = "VALID" if self.is_valid else "INVALID"
        return (
            f"ValidationResult({status}, "
            f"{len(self.errors)} errors, "
            f"{len(self.warnings)} warnings)"
        )


# ---------------------------------------------------------------------------
# Individual field validators (private helpers)
# ---------------------------------------------------------------------------

def _check_positive(result: ValidationResult, value: float, name: str) -> None:
    """Block if value is not strictly positive."""
    if value <= 0:
        result.add_error(
            f"'{name}' deve ser estritamente positivo. "
            f"Valor recebido: {value:.4g}."
        )


def _check_thickness(result: ValidationResult, t: float) -> None:
    """Block if thickness is outside a physically meaningful range."""
    _check_positive(result, t, "Espessura (t)")
    if t > 0 and not (0.1 <= t <= 20.0):
        result.add_error(
            f"Espessura t = {t} mm está fora do intervalo suportado "
            f"(0.1 mm – 20.0 mm)."
        )


def _check_flange_diameter(
    result: ValidationResult,
    d_f: float,
    d_i: float,
    t: float,
    r_die: float,
) -> None:
    """
    Block if flange diameter is not large enough to form a valid flange.

    Two requirements:
      1. d_f > d_i + 2*t          (flange width >= t on each side, absolute minimum).
      2. d_f >= d_i + 2*t + 2*r_die  (enough room for the die fillet radius).
    """
    if d_f <= 0:
        return

    # Requirement 1 — absolute minimum
    min_d_f_1 = d_i + 2.0 * t
    if d_f <= min_d_f_1:
        result.add_error(
            f"Diâmetro da aba d_f = {d_f:.2f} mm é insuficiente. "
            f"É necessário d_f > d_i + 2t = {min_d_f_1:.2f} mm "
            f"para que exista uma aba mínima de espessura t em cada lado."
        )
        return

    # Requirement 2 — die fillet must fit within the flange width
    min_d_f_2 = d_i + 2.0 * t + 2.0 * r_die
    if d_f < min_d_f_2 - 1e-9:
        result.add_error(
            f"Diâmetro da aba d_f = {d_f:.2f} mm é insuficiente para acomodar "
            f"o raio da matriz r_die = {r_die:.1f} mm. "
            f"O mínimo necessário é d_f ≥ d_i + 2t + 2·r_die = {min_d_f_2:.2f} mm. "
            "Valores menores produzem geometria degenerada no contorno do filete da matriz."
        )


def _check_die_radius(result: ValidationResult, r_die: float, t: float) -> None:
    """
    Block if die radius is below absolute minimum (2t).
    Warn if below recommended value (4t).
    """
    if r_die <= 0 or t <= 0:
        return  # handled elsewhere

    min_r = MIN_DIE_RADIUS_FACTOR * t
    rec_r = RECOMMENDED_DIE_RADIUS_FACTOR * t

    if r_die < min_r:
        result.add_error(
            f"Raio da matriz r_die = {r_die:.2f} mm é menor que o mínimo "
            f"absoluto de {MIN_DIE_RADIUS_FACTOR:.0f}t = {min_r:.2f} mm. "
            "Raios menores causam fratura na borda da peça."
        )
    elif r_die < rec_r:
        result.add_warning(
            f"Raio da matriz r_die = {r_die:.2f} mm está abaixo do valor "
            f"recomendado de {RECOMMENDED_DIE_RADIUS_FACTOR:.0f}t = {rec_r:.2f} mm. "
            "Considere aumentar para reduzir o risco de fratura."
        )


def _check_minimum_height(
    result: ValidationResult,
    H: float,
    r_punch: float,
    r_die: float,
    t: float,
) -> None:
    """
    Block if H is too small to accommodate the punch and die fillet radii.

    The punch fillet has a vertical extent of r_punch, and the die fillet
    has a vertical extent of r_die. The wall must have at least zero
    straight length between them:

        inner wall:  y ∈ [r_punch,  H - r_die]        → H >= r_punch + r_die
        outer wall:  y ∈ [H - t - r_die,  r_punch]    → H >= r_punch + r_die + t

    When H < r_punch + r_die + t, the rendered wall segments invert or
    overlap (inverted outer wall, die fillet arcs below bottom of cup).
    """
    if H <= 0 or r_punch <= 0 or r_die <= 0 or t <= 0:
        return
    min_H = r_punch + r_die + t
    if H < min_H:
        result.add_error(
            f"Altura H = {H:.2f} mm é insuficiente. "
            f"O mínimo necessário para acomodar os raios do punção ({r_punch:.2f} mm) "
            f"e da matriz ({r_die:.2f} mm) com espessura t = {t:.2f} mm "
            f"é H ≥ r_punção + r_matriz + t = {min_H:.2f} mm. "
            "Valores menores produzem geometria degenerada (paredes invertidas)."
        )


def _check_punch_radius(
    result: ValidationResult,
    r_punch: float,
    t: float,
    d_i: float,
) -> None:
    """
    Block if punch radius is below absolute minimum (2t).
    Warn if below recommended value (3t).
    Error if r_punch >= d_i/2 (no flat bottom — degenerate geometry).
    """
    if r_punch <= 0 or t <= 0 or d_i <= 0:
        return

    min_r = MIN_PUNCH_RADIUS_FACTOR * t
    rec_r = RECOMMENDED_PUNCH_RADIUS_FACTOR * t

    if r_punch < min_r:
        result.add_error(
            f"Raio do punção r_punch = {r_punch:.2f} mm é menor que o mínimo "
            f"absoluto de {MIN_PUNCH_RADIUS_FACTOR:.0f}t = {min_r:.2f} mm. "
            "Raios menores causam fratura no fundo da peça."
        )
        return

    if r_punch < rec_r:
        result.add_warning(
            f"Raio do punção r_punch = {r_punch:.2f} mm está abaixo do valor "
            f"recomendado de {RECOMMENDED_PUNCH_RADIUS_FACTOR:.0f}t = {rec_r:.2f} mm. "
            "Considere aumentar para melhorar o fluxo de material."
        )

    # r_punch >= d_i/2 eliminates the flat bottom entirely
    if r_punch >= d_i / 2.0:
        result.add_error(
            f"Raio do punção r_punch = {r_punch:.2f} mm deve ser menor que "
            f"d_i/2 = {d_i/2:.2f} mm para que exista um fundo plano. "
            "Com r_punch ≥ d_i/2 a geometria torna-se degenerada "
            "(todo o fundo é consumido pelo raio de concordância)."
        )


def _check_material_properties(
    result: ValidationResult,
    uts: float,
    ys: float,
) -> None:
    """Block if material stress values are physically inconsistent."""
    if uts <= 0:
        result.add_error(
            f"UTS (Resistência à Tração) deve ser > 0 MPa. Valor: {uts:.4g}."
        )
    if ys <= 0:
        result.add_error(
            f"Ys (Limite de Escoamento) deve ser > 0 MPa. Valor: {ys:.4g}."
        )
    if uts > 0 and ys > 0 and ys > uts:
        result.add_error(
            f"Limite de escoamento Ys = {ys:.1f} MPa não pode ser maior "
            f"que a resistência à tração UTS = {uts:.1f} MPa."
        )


def _check_drawing_coefficients(
    result: ValidationResult,
    m1_lim: float,
    mn_lim: float,
) -> None:
    """Block if drawing coefficients are outside physically meaningful ranges."""
    if not (0.35 <= m1_lim <= 0.70):
        result.add_error(
            f"Coeficiente de repuxo do 1º passe m1_lim = {m1_lim:.3f} "
            "deve estar entre 0.35 e 0.70."
        )
    if not (0.55 <= mn_lim <= 0.95):
        result.add_error(
            f"Coeficiente de repuxo subsequente mn_lim = {mn_lim:.3f} "
            "deve estar entre 0.55 e 0.95."
        )
    if (0.35 <= m1_lim <= 0.70) and (0.55 <= mn_lim <= 0.95):
        if mn_lim <= m1_lim:
            result.add_error(
                f"mn_lim ({mn_lim:.3f}) deve ser maior que m1_lim ({m1_lim:.3f}). "
                "Os passes subsequentes são menos severos que o primeiro."
            )


def _check_severity_t_d_ratio(
    result: ValidationResult,
    t: float,
    d_b_estimated: float,
) -> None:
    """
    Warn if t/D ratio indicates extreme sensitivity to wrinkling.

    Note: This uses a rough estimate of D_b = sqrt(d_i^2 + 4*d_i*H + d_f^2)
    since the full blank is not computed here. A precise check is done
    inside blank_calculator.py after the blank is known.
    """
    if t <= 0 or d_b_estimated <= 0:
        return
    ratio_pct = (t / d_b_estimated) * 100.0
    if ratio_pct < T_D_RATIO_YELLOW:
        result.add_warning(
            f"Relação t/D estimada ≈ {ratio_pct:.2f}% está abaixo de "
            f"{T_D_RATIO_YELLOW}%. O processo é extremamente sensível a rugas "
            "e exige controle preciso da pressão do prensa-chapas."
        )


def _check_drawability(
    result: ValidationResult,
    d_i: float,
    d_f: float,
    H: float,
    t: float,
    m1_lim: float,
) -> None:
    """
    Warn if the part appears extremely difficult to draw
    (very deep relative height or very wide flange).
    """
    if d_i <= 0 or H <= 0:
        return

    # Neutral diameter (mid-plane of wall)
    d_neutral = d_i + t
    h_d_ratio = H / d_neutral

    if h_d_ratio > DR_YELLOW:
        result.add_warning(
            f"Relação H/d = {h_d_ratio:.2f} indica uma peça muito profunda "
            f"(deep drawing severo). Espere {int(1/m1_lim + (h_d_ratio - 1)/0.5) + 1} "
            "ou mais passes de conformação."
        )

    if d_f > 0 and d_neutral > 0:
        df_d = d_f / d_neutral
        if df_d > 2.5:
            result.add_warning(
                f"Relação df/d = {df_d:.2f} indica uma aba muito larga. "
                "O primeiro passe será condicionado pelo diâmetro da aba, "
                "não pela altura da peça. Verifique a sequência de passes com atenção."
            )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate_inputs(
    d_i: float,
    H: float,
    d_f: float,
    t: float,
    r_die: float,
    r_punch: float,
    uts: float,
    ys: float,
    m1_lim: float,
    mn_lim: float,
) -> ValidationResult:
    """
    Validate all user inputs for the cylindrical drawing calculator.

    Performs structural, geometric and physical plausibility checks.
    Returns a ValidationResult with lists of errors and warnings.
    Does NOT raise exceptions.

    Args:
        d_i     : Internal diameter of finished part (mm).
        H       : Wall height of finished part (mm).
        d_f     : Flange outer diameter (mm).
        t       : Sheet thickness (mm).
        r_die   : Die corner radius (mm).
        r_punch : Punch corner radius (mm).
        uts     : Ultimate Tensile Strength (MPa).
        ys      : Yield Strength (MPa).
        m1_lim  : Limiting drawing coefficient — 1st pass (dimensionless).
        mn_lim  : Limiting drawing coefficient — subsequent passes (dimensionless).

    Returns:
        ValidationResult instance. Use .is_valid, .errors, .warnings.
    """
    result = ValidationResult()

    # ---- Geometric inputs: must be positive --------------------------------
    _check_positive(result, d_i, "Diâmetro interno (d_i)")
    _check_positive(result, H,   "Altura final (H)")
    _check_positive(result, d_f, "Diâmetro da aba (d_f)")
    _check_positive(result, r_die,   "Raio da matriz (r_die)")
    _check_positive(result, r_punch, "Raio do punção (r_punch)")

    # ---- Thickness ---------------------------------------------------------
    _check_thickness(result, t)

    # ---- Flange diameter consistency ---------------------------------------
    # Only check if basic positivity already passed
    if d_f > 0 and d_i > 0 and t > 0:
        _check_flange_diameter(result, d_f, d_i, t, r_die)

    # ---- Tool radii --------------------------------------------------------
    if t > 0:
        _check_die_radius(result, r_die, t)
        _check_punch_radius(result, r_punch, t, d_i)

    # ---- Minimum wall height (geometric constraint) ------------------------
    _check_minimum_height(result, H, r_punch, r_die, t)

    # ---- Material properties -----------------------------------------------
    _check_material_properties(result, uts, ys)

    # ---- Drawing coefficients ----------------------------------------------
    _check_drawing_coefficients(result, m1_lim, mn_lim)

    # ---- Severity / process warnings (non-blocking) ------------------------
    # Rough blank diameter estimate for t/D check (before full calculation)
    if d_i > 0 and H > 0 and d_f > 0 and t > 0:
        import math
        d_b_est = math.sqrt(d_i**2 + 4.0 * d_i * H + d_f**2)
        _check_severity_t_d_ratio(result, t, d_b_est)
        _check_drawability(result, d_i, d_f, H, t, m1_lim)

    return result


def validate_pass_heights(
    seq_res,
    r_punch: float,
    r_die: float,
    t: float,
    d_i: float,
    d_f: float,
    m1_lim: float,
    mn_lim: float,
    trim_fraction: float = 0.03,
) -> ValidationResult:
    """
    Validate that every pass in the sequence has sufficient wall height
    to avoid rendering glitches (inverted wall segments, overlapping arcs).

    Intermediate passes can have heights significantly lower than the
    final H, especially the first pass when the blank is close to the
    flange diameter. They must still be >= r_punch + r_die + t.

    If any pass fails, this function estimates a minimum viable H for
    the final product and includes it in the error message.

    Args:
        seq_res      : PassSequenceResult from compute_pass_sequence().
        r_punch      : Punch corner radius (mm).
        r_die        : Die corner radius (mm).
        t            : Sheet thickness (mm).
        d_i          : Internal diameter (mm) — for estimation.
        d_f          : Flange outer diameter (mm) — for estimation.
        m1_lim       : 1st-pass drawing coefficient — for estimation.
        mn_lim       : Subsequent-pass drawing coefficient — for estimation.
        trim_fraction: Blank trim allowance fraction — for estimation.

    Returns:
        ValidationResult. If non-empty, the calculation should be blocked.
    """
    result = ValidationResult()

    min_height = r_punch + r_die + t
    low_passes = []

    for p in seq_res.passes:
        if p.height < min_height:
            low_passes.append(p.pass_number)

    if not low_passes:
        return result

    # Estimate minimum viable H for the final product
    min_H_suggested = _estimate_min_H(
        d_i=d_i, d_f=d_f, t=t,
        r_punch=r_punch, r_die=r_die,
        m1_lim=m1_lim, mn_lim=mn_lim,
        trim_fraction=trim_fraction,
    )

    if len(low_passes) == 1:
        msg = (
            f"O passe {low_passes[0]} tem altura insuficiente para os "
            f"raios do punção ({r_punch:.1f} mm) e da matriz ({r_die:.1f} mm) "
            f"com espessura t = {t:.1f} mm. "
            f"Aumente a altura final H para pelo menos {min_H_suggested:.1f} mm."
        )
    else:
        passes_str = ", ".join(str(pn) for pn in low_passes)
        msg = (
            f"Os passes {passes_str} têm altura insuficiente para os "
            f"raios do punção ({r_punch:.1f} mm) e da matriz ({r_die:.1f} mm) "
            f"com espessura t = {t:.1f} mm. "
            f"Aumente a altura final H para pelo menos {min_H_suggested:.1f} mm."
        )

    result.add_error(msg)
    return result


def _estimate_min_H(
    d_i: float,
    d_f: float,
    t: float,
    r_punch: float,
    r_die: float,
    m1_lim: float,
    mn_lim: float,
    trim_fraction: float = 0.03,
) -> float:
    """
    Find the minimum final-part height H such that every pass has
    height >= r_punch + r_die + t.

    Uses iterative search with a growing step. Converges quickly
    because the first-pass height is roughly proportional to H.
    """
    from blank_calculator import compute_blank
    from pass_sequence import compute_pass_sequence

    min_height = r_punch + r_die + t
    H = max(min_height, 1.0)

    # Step grows geometrically (1.3x) to bracket the right value fast
    step = max(5.0, H * 0.2)

    for _ in range(50):
        blank = compute_blank(
            d_i=d_i, H=H, d_f=d_f, t=t,
            r_punch=r_punch, trim_fraction=trim_fraction,
        )
        seq = compute_pass_sequence(
            d_blank=blank.d_blank_final,
            d_i=d_i, H=H, t=t,
            r_die_final=r_die, r_punch_final=r_punch,
            m1_lim=m1_lim, mn_lim=mn_lim,
            d_f=d_f,
        )

        all_ok = True
        for p in seq.passes:
            if p.height < min_height - 0.01:
                all_ok = False
                break

        if all_ok:
            return round(H, 1)

        H += step
        step *= 1.3

    return round(H, 1)


def validate_custom_material(uts: float, ys: float) -> ValidationResult:
    """
    Lightweight validation for custom material stress values only.

    Useful for real-time feedback in the Streamlit UI when the user
    selects 'Personalizado' and types UTS/Ys values.

    Args:
        uts: Ultimate Tensile Strength (MPa).
        ys:  Yield Strength (MPa).

    Returns:
        ValidationResult instance.
    """
    result = ValidationResult()
    _check_material_properties(result, uts, ys)
    return result
