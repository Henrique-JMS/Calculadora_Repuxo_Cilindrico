"""
tests/test_process_data.py
===========================
Unit tests for process_data.py
"""

import math
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from blank_calculator import compute_blank
from pass_sequence import compute_pass_sequence
from process_data import (
    compute_process_data,
    ProcessDataResult,
    PassForces,
    SeverityIndicators,
    _punch_force,
    _bh_contact_area,
    _bh_pressure,
    _extraction_force,
    _press_capacity,
    _energy,
)
from constants import (
    SIEBEL_CORRECTION,
    EXTRACTION_FORCE_FACTOR,
    DEFAULT_SAFETY_FACTOR,
    BH_PRESSURE_COEFF,
    PRESS_EFFICIENCY,
)


# ---------------------------------------------------------------------------
# Shared fixture — compute a full chain for a standard part
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def standard_result():
    """Full chain: blank → passes → process data for a standard steel cup."""
    blank = compute_blank(
        d_i=80.0, H=60.0, d_f=120.0, t=1.5, r_punch=4.5, trim_fraction=0.03
    )
    seq = compute_pass_sequence(
        d_blank=blank.d_blank_final,
        d_i=80.0, H=60.0, t=1.5,
        r_die_final=6.0, r_punch_final=4.5,
        m1_lim=0.50, mn_lim=0.75,
        d_f=120.0,
    )
    result = compute_process_data(
        passes_geom=seq.passes,
        d_blank=blank.d_blank_final,
        d_f=120.0, H=60.0, t=1.5,
        uts=310.0, ys=175.0,
    )
    return result


# ---------------------------------------------------------------------------
# Force formula unit tests (private helpers)
# ---------------------------------------------------------------------------

class TestForceFormulas:

    def test_punch_force_formula(self):
        # F = π * d * t * UTS * (DR - 0.7)
        F = _punch_force(d_after=80.0, t=1.5, uts=310.0, dr=2.0)
        expected = math.pi * 80.0 * 1.5 * 310.0 * (2.0 - SIEBEL_CORRECTION)
        assert F == pytest.approx(expected, rel=1e-6)

    def test_punch_force_increases_with_dr(self):
        F1 = _punch_force(80.0, 1.5, 310.0, dr=1.5)
        F2 = _punch_force(80.0, 1.5, 310.0, dr=2.0)
        assert F2 > F1

    def test_punch_force_increases_with_uts(self):
        F1 = _punch_force(80.0, 1.5, 200.0, dr=2.0)
        F2 = _punch_force(80.0, 1.5, 400.0, dr=2.0)
        assert F2 == pytest.approx(2.0 * F1, rel=1e-6)

    def test_punch_force_zero_for_dr_equal_correction(self):
        F = _punch_force(80.0, 1.5, 310.0, dr=SIEBEL_CORRECTION)
        assert F == pytest.approx(0.0, abs=1e-6)

    def test_bh_contact_area_formula(self):
        # A = π/4 * (D_before² - (d_after + 2*r_die)²)
        A = _bh_contact_area(d_before=160.0, d_after=80.0, r_die=6.0)
        d_inner = 80.0 + 2.0 * 6.0  # 92
        expected = math.pi / 4.0 * (160.0**2 - 92.0**2)
        assert A == pytest.approx(expected, rel=1e-6)

    def test_bh_contact_area_zero_when_d_before_too_small(self):
        A = _bh_contact_area(d_before=90.0, d_after=80.0, r_die=6.0)
        # d_inner = 92 > 90 → area = 0
        assert A == pytest.approx(0.0, abs=1e-9)

    def test_bh_contact_area_positive_for_valid(self):
        A = _bh_contact_area(d_before=160.0, d_after=80.0, r_die=6.0)
        assert A > 0

    def test_bh_pressure_formula(self):
        p = _bh_pressure(ys=175.0)
        assert p == pytest.approx(BH_PRESSURE_COEFF * 175.0, rel=1e-9)

    def test_extraction_force_fraction(self):
        F_ext = _extraction_force(F_punch=10000.0)
        assert F_ext == pytest.approx(EXTRACTION_FORCE_FACTOR * 10000.0, rel=1e-9)

    def test_press_capacity_formula(self):
        F = _press_capacity(F_punch=10000.0, F_bh=5000.0, safety_factor=1.25)
        assert F == pytest.approx(15000.0 * 1.25, rel=1e-9)

    def test_energy_input_formula(self):
        # Input energy = F_punch × height / (1000 × η)
        F = 10000.0   # N
        H = 60.0      # mm
        W = _energy(F, H)
        expected = F * H / (1000.0 * PRESS_EFFICIENCY)
        assert W == pytest.approx(expected, rel=1e-9)

    def test_energy_greater_than_mechanical_work(self):
        # Since η < 1, input energy must be > F × H / 1000
        F = 10000.0
        H = 60.0
        W = _energy(F, H)
        mech_work = F * H / 1000.0
        assert W > mech_work
        assert W == pytest.approx(mech_work / PRESS_EFFICIENCY, rel=1e-9)

    def test_energy_scales_linearly_with_force(self):
        W1 = _energy(5000.0, 60.0)
        W2 = _energy(10000.0, 60.0)
        assert W2 == pytest.approx(2.0 * W1, rel=1e-9)

    def test_energy_scales_linearly_with_height(self):
        W1 = _energy(10000.0, 30.0)
        W2 = _energy(10000.0, 60.0)
        assert W2 == pytest.approx(2.0 * W1, rel=1e-9)

    def test_energy_zero_for_zero_force(self):
        assert _energy(0.0, 60.0) == pytest.approx(0.0, abs=1e-9)


# ---------------------------------------------------------------------------
# compute_process_data — output structure
# ---------------------------------------------------------------------------

class TestOutputStructure:

    def test_returns_process_data_result(self, standard_result):
        assert isinstance(standard_result, ProcessDataResult)

    def test_passes_is_list(self, standard_result):
        assert isinstance(standard_result.passes, list)

    def test_severity_is_severity_indicators(self, standard_result):
        assert isinstance(standard_result.severity, SeverityIndicators)

    def test_each_pass_is_pass_forces(self, standard_result):
        for pf in standard_result.passes:
            assert isinstance(pf, PassForces)

    def test_pass_numbers_sequential(self, standard_result):
        for i, pf in enumerate(standard_result.passes, start=1):
            assert pf.pass_number == i


# ---------------------------------------------------------------------------
# Force values — physical plausibility
# ---------------------------------------------------------------------------

class TestForceValues:

    def test_punch_force_positive(self, standard_result):
        for pf in standard_result.passes:
            assert pf.F_punch_N >= 0

    def test_bh_force_nonnegative(self, standard_result):
        for pf in standard_result.passes:
            assert pf.F_blank_holder_N >= 0

    def test_extraction_force_positive(self, standard_result):
        for pf in standard_result.passes:
            assert pf.F_extraction_N >= 0

    def test_press_capacity_positive(self, standard_result):
        for pf in standard_result.passes:
            assert pf.F_press_N > 0

    def test_press_force_greater_than_punch_force(self, standard_result):
        for pf in standard_result.passes:
            assert pf.F_press_N >= pf.F_punch_N

    def test_kN_consistent_with_N(self, standard_result):
        for pf in standard_result.passes:
            assert pf.F_punch_kN == pytest.approx(pf.F_punch_N / 1000.0, rel=1e-4)

    def test_tonf_consistent_with_N(self, standard_result):
        for pf in standard_result.passes:
            assert pf.F_press_tonf == pytest.approx(pf.F_press_N / 9806.65, rel=1e-3)

    def test_energy_positive(self, standard_result):
        for pf in standard_result.passes:
            assert pf.energy_J >= 0

    def test_peak_press_kN_equals_max_across_passes(self, standard_result):
        expected = max(pf.F_press_kN for pf in standard_result.passes)
        assert standard_result.peak_press_kN == pytest.approx(expected, rel=1e-4)


# ---------------------------------------------------------------------------
# Severity indicators
# ---------------------------------------------------------------------------

class TestSeverityIndicators:

    def test_t_D_ratio_positive(self, standard_result):
        assert standard_result.severity.t_D_ratio_pct > 0

    def test_severity_strings_valid(self, standard_result):
        s = standard_result.severity
        for attr in ("severity_t_D", "severity_DR", "severity_df_d", "severity_H_d"):
            assert getattr(s, attr) in ("green", "yellow", "red")

    def test_n_passes_matches_passes_list(self, standard_result):
        assert standard_result.severity.n_passes == len(standard_result.passes)

    def test_df_d_ratio_positive(self, standard_result):
        assert standard_result.severity.df_d_ratio > 0

    def test_H_d_ratio_positive(self, standard_result):
        assert standard_result.severity.H_d_ratio > 0

    def test_DR_first_positive(self, standard_result):
        assert standard_result.severity.DR_first > 1.0  # always > 1 by definition


# ---------------------------------------------------------------------------
# Safety factor sensitivity
# ---------------------------------------------------------------------------

class TestSafetyFactor:

    def test_higher_safety_factor_gives_higher_press_capacity(self):
        blank = compute_blank(d_i=80.0, H=60.0, d_f=120.0, t=1.5, r_punch=4.5)
        seq   = compute_pass_sequence(
            d_blank=blank.d_blank_final,
            d_i=80.0, H=60.0, t=1.5,
            r_die_final=6.0, r_punch_final=4.5,
            m1_lim=0.50, mn_lim=0.75,
            d_f=120.0,
        )
        r1 = compute_process_data(
            seq.passes, blank.d_blank_final, 120.0, 60.0, 1.5, 310.0, 175.0,
            safety_factor=1.0,
        )
        r2 = compute_process_data(
            seq.passes, blank.d_blank_final, 120.0, 60.0, 1.5, 310.0, 175.0,
            safety_factor=1.5,
        )
        assert r2.peak_press_kN > r1.peak_press_kN
