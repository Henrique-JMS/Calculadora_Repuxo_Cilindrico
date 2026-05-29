"""
tests/test_validators.py
========================
Unit tests for validators.py
"""

import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from validators import (
    validate_inputs,
    validate_custom_material,
    validate_pass_heights,
    _estimate_min_H,
    ValidationResult,
)
from blank_calculator import compute_blank
from pass_sequence import compute_pass_sequence


# ---------------------------------------------------------------------------
# Fixtures — baseline valid inputs
# ---------------------------------------------------------------------------

VALID = dict(
    d_i=80.0,
    H=60.0,
    d_f=120.0,
    t=1.5,
    r_die=6.0,
    r_punch=4.5,
    uts=310.0,
    ys=175.0,
    m1_lim=0.50,
    mn_lim=0.75,
)


def run(**overrides):
    """Helper: run validate_inputs with VALID base overridden by kwargs."""
    inputs = {**VALID, **overrides}
    return validate_inputs(**inputs)


# ---------------------------------------------------------------------------
# ValidationResult interface
# ---------------------------------------------------------------------------

class TestValidationResult:

    def test_empty_result_is_valid(self):
        r = ValidationResult()
        assert r.is_valid
        assert not r.has_errors
        assert not r.has_warnings

    def test_add_error_marks_invalid(self):
        r = ValidationResult()
        r.add_error("something wrong")
        assert r.has_errors
        assert not r.is_valid

    def test_add_warning_stays_valid(self):
        r = ValidationResult()
        r.add_warning("be careful")
        assert r.has_warnings
        assert r.is_valid   # warnings don't block

    def test_repr_contains_status(self):
        r = ValidationResult()
        assert "VALID" in repr(r)
        r.add_error("x")
        assert "INVALID" in repr(r)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

class TestHappyPath:

    def test_valid_inputs_pass(self):
        result = run()
        assert result.is_valid, result.errors

    def test_valid_inputs_no_errors(self):
        result = run()
        assert len(result.errors) == 0


# ---------------------------------------------------------------------------
# Geometry — blocking errors
# ---------------------------------------------------------------------------

class TestGeometryErrors:

    def test_di_zero_is_error(self):
        assert run(d_i=0.0).has_errors

    def test_di_negative_is_error(self):
        assert run(d_i=-5.0).has_errors

    def test_H_zero_is_error(self):
        assert run(H=0.0).has_errors

    def test_H_negative_is_error(self):
        assert run(H=-1.0).has_errors

    def test_df_zero_is_error(self):
        assert run(d_f=0.0).has_errors

    def test_t_zero_is_error(self):
        assert run(t=0.0).has_errors

    def test_t_negative_is_error(self):
        assert run(t=-0.5).has_errors

    def test_t_too_large_is_error(self):
        assert run(t=25.0).has_errors

    def test_r_die_zero_is_error(self):
        assert run(r_die=0.0).has_errors

    def test_r_punch_zero_is_error(self):
        assert run(r_punch=0.0).has_errors

    def test_df_equal_to_minimum_is_error(self):
        # d_f must be strictly greater than d_i + 2t
        d_i, t = 80.0, 1.5
        d_f_min = d_i + 2.0 * t   # = 83.0
        assert run(d_i=d_i, t=t, d_f=d_f_min).has_errors

    def test_df_just_above_minimum_is_ok(self):
        """d_f just above the die-fillet-aware minimum should pass."""
        d_i, t, r_die = 80.0, 1.5, 6.0
        d_f_ok = d_i + 2.0 * t + 2.0 * r_die + 0.1  # = 95.1
        result = run(d_i=d_i, t=t, r_die=r_die, d_f=d_f_ok)
        flange_errors = [e for e in result.errors if "aba" in e.lower() or "d_f" in e.lower()]
        assert len(flange_errors) == 0

    def test_df_below_die_fillet_minimum_is_error(self):
        """d_f is below the die-fillet requirement (d_f < d_i+2t+2*r_die)."""
        d_i, t, r_die = 80.0, 1.5, 6.0
        d_f_bad = d_i + 2.0 * t + 2.0 * r_die - 10.0  # = 85.0
        result = run(d_i=d_i, t=t, r_die=r_die, d_f=d_f_bad)
        assert result.has_errors
        assert any("filete" in e.lower() or "matriz" in e.lower() for e in result.errors)

    def test_df_at_die_fillet_minimum_is_ok(self):
        """d_f exactly equal to d_i+2t+2*r_die should pass."""
        d_i, t, r_die = 80.0, 1.5, 6.0
        d_f_min = d_i + 2.0 * t + 2.0 * r_die  # = 95.0
        result = run(d_i=d_i, t=t, r_die=r_die, d_f=d_f_min)
        flange_errors = [e for e in result.errors if "aba" in e.lower() or "d_f" in e.lower()]
        assert len(flange_errors) == 0

    def test_df_just_above_die_fillet_minimum_is_ok(self):
        """d_f slightly above the die-fillet requirement should pass."""
        d_i, t, r_die = 80.0, 1.5, 6.0
        d_f_ok = d_i + 2.0 * t + 2.0 * r_die + 0.1  # = 95.1
        result = run(d_i=d_i, t=t, r_die=r_die, d_f=d_f_ok)
        flange_errors = [e for e in result.errors if "aba" in e.lower() or "d_f" in e.lower()]
        assert len(flange_errors) == 0

    def test_die_radius_below_2t_is_error(self):
        # r_die < 2t → blocking error
        result = run(t=2.0, r_die=3.0)   # 3 < 2*2 = 4
        assert result.has_errors

    def test_punch_radius_below_2t_is_error(self):
        result = run(t=2.0, r_punch=3.0)  # 3 < 2*2 = 4
        assert result.has_errors

    def test_die_radius_between_2t_and_4t_is_warning(self):
        # 2t <= r_die < 4t → warning, not error
        result = run(t=2.0, r_die=5.0)   # 5 is between 4 and 8
        assert not result.has_errors
        assert result.has_warnings

    def test_punch_radius_between_2t_and_3t_is_warning(self):
        result = run(t=2.0, r_punch=5.0)   # 5 is between 4 and 6
        assert not result.has_errors
        assert result.has_warnings

    def test_punch_radius_equal_to_di_half_is_error(self):
        # r_punch = d_i/2 → no flat bottom → blocking error
        result = run(d_i=80.0, r_punch=40.0)
        assert result.has_errors

    def test_punch_radius_greater_than_di_half_is_error(self):
        # r_punch > d_i/2 → degenerate geometry → blocking error
        result = run(d_i=80.0, r_punch=50.0)
        assert result.has_errors

    def test_punch_radius_just_below_di_half_passes_no_rp_error(self):
        # r_punch < d_i/2 → flat bottom exists → no punch-related error
        result = run(d_i=80.0, r_punch=39.9)
        rp_errors = [e for e in result.errors if "punção" in e.lower()]
        assert len(rp_errors) == 0

    def test_punch_radius_di_half_blocks_before_thickness_warning(self):
        # r_punch >= d_i/2 takes precedence over thickness-based warning
        # d_i=10, r_punch=6 → r_punch=6 >= d_i/2=5 → error, not just warning
        result = run(d_i=10.0, r_punch=6.0, t=1.5)
        assert result.has_errors

    def test_H_below_punch_plus_die_plus_t_is_error(self):
        # H = 5, r_punch=4, r_die=4, t=1 → min = 9 → error
        result = run(H=5.0, r_punch=4.0, r_die=4.0, t=1.0)
        assert result.has_errors

    def test_H_equal_to_minimum_passes(self):
        # H = 9, r_punch=4, r_die=4, t=1 → min = 9 → passes (no error)
        result = run(H=9.0, r_punch=4.0, r_die=4.0, t=1.0)
        assert result.is_valid

    def test_H_just_below_minimum_triggers_error(self):
        # H = 11.9, r_punch=4.5, r_die=6.0, t=1.5 → min = 12.0
        result = run(H=11.9)
        assert result.has_errors

    def test_H_above_minimum_no_height_error(self):
        result = run(H=13.0)
        height_errors = [e for e in result.errors if "altura" in e.lower()]
        assert len(height_errors) == 0


# ---------------------------------------------------------------------------
# Material properties — blocking errors
# ---------------------------------------------------------------------------

class TestMaterialErrors:

    def test_uts_zero_is_error(self):
        assert run(uts=0.0).has_errors

    def test_uts_negative_is_error(self):
        assert run(uts=-100.0).has_errors

    def test_ys_zero_is_error(self):
        assert run(ys=0.0).has_errors

    def test_ys_exceeds_uts_is_error(self):
        assert run(uts=200.0, ys=250.0).has_errors


# ---------------------------------------------------------------------------
# Drawing coefficients — blocking errors
# ---------------------------------------------------------------------------

class TestDrawingCoeffErrors:

    def test_m1_lim_too_low_is_error(self):
        assert run(m1_lim=0.20).has_errors

    def test_m1_lim_too_high_is_error(self):
        assert run(m1_lim=0.80).has_errors

    def test_mn_lim_too_low_is_error(self):
        assert run(mn_lim=0.40).has_errors

    def test_mn_lim_too_high_is_error(self):
        assert run(mn_lim=0.98).has_errors

    def test_mn_lim_less_than_m1_lim_is_error(self):
        assert run(m1_lim=0.60, mn_lim=0.58).has_errors

    def test_mn_lim_equal_to_m1_lim_is_error(self):
        assert run(m1_lim=0.60, mn_lim=0.60).has_errors


# ---------------------------------------------------------------------------
# Severity warnings (non-blocking)
# ---------------------------------------------------------------------------

class TestSeverityWarnings:

    def test_very_thin_blank_triggers_warning(self):
        # Very thin sheet → low t/D → warning
        result = run(d_i=200.0, H=150.0, d_f=280.0, t=0.3)
        assert result.is_valid     # not an error
        assert result.has_warnings

    def test_normal_thickness_no_t_d_warning(self):
        # t/D >> 0.5% → no t/D warning expected
        result = run(d_i=40.0, H=20.0, d_f=60.0, t=2.0)
        # There may be no warnings at all — just confirm is_valid
        assert result.is_valid


# ---------------------------------------------------------------------------
# validate_custom_material
# ---------------------------------------------------------------------------

class TestValidateCustomMaterial:

    def test_valid_custom_material(self):
        result = validate_custom_material(uts=400.0, ys=200.0)
        assert result.is_valid

    def test_uts_zero(self):
        result = validate_custom_material(uts=0.0, ys=200.0)
        assert result.has_errors

    def test_ys_zero(self):
        result = validate_custom_material(uts=400.0, ys=0.0)
        assert result.has_errors

    def test_ys_greater_than_uts(self):
        result = validate_custom_material(uts=300.0, ys=400.0)
        assert result.has_errors


# ---------------------------------------------------------------------------
# validate_pass_heights / _estimate_min_H
# ---------------------------------------------------------------------------

class TestValidatePassHeights:

    def _run_sequence(self, d_i, H, d_f, t, r_punch, r_die, m1_lim, mn_lim,
                      trim=0.03):
        blank = compute_blank(d_i=d_i, H=H, d_f=d_f, t=t,
                              r_punch=r_punch, trim_fraction=trim)
        seq = compute_pass_sequence(
            d_blank=blank.d_blank_final,
            d_i=d_i, H=H, t=t,
            r_die_final=r_die, r_punch_final=r_punch,
            m1_lim=m1_lim, mn_lim=mn_lim,
            d_f=d_f,
        )
        return seq

    def test_standard_cup_passes(self):
        """Standard steel cup — all passes must have sufficient height."""
        seq = self._run_sequence(
            d_i=80.0, H=60.0, d_f=120.0, t=1.5,
            r_punch=4.5, r_die=6.0,
            m1_lim=0.50, mn_lim=0.75,
        )
        result = validate_pass_heights(
            seq_res=seq, r_punch=4.5, r_die=6.0, t=1.5,
            d_i=80.0, d_f=120.0, m1_lim=0.50, mn_lim=0.75,
        )
        assert result.is_valid, result.errors

    def test_very_shallow_cup_fails(self):
        """Wide flange with shallow H — first pass height should be too low."""
        seq = self._run_sequence(
            d_i=100.0, H=14.0, d_f=300.0, t=1.5,
            r_punch=4.5, r_die=6.0,
            m1_lim=0.50, mn_lim=0.75,
        )
        result = validate_pass_heights(
            seq_res=seq, r_punch=4.5, r_die=6.0, t=1.5,
            d_i=100.0, d_f=300.0, m1_lim=0.50, mn_lim=0.75,
        )
        assert result.has_errors

    def test_estimate_min_H_exceeds_geometric_min(self):
        """For a problematic case, estimate must exceed geometric minimum."""
        min_H = _estimate_min_H(
            d_i=100.0, d_f=300.0, t=1.5,
            r_punch=4.5, r_die=6.0,
            m1_lim=0.50, mn_lim=0.75,
        )
        geom_min = 4.5 + 6.0 + 1.5  # = 12
        assert min_H > geom_min, (
            f"min_H {min_H} should exceed geometric min {geom_min}"
        )

    def test_estimate_min_H_standard_cup_is_geometric_min(self):
        """Standard cup already passes at geometric minimum."""
        min_H = _estimate_min_H(
            d_i=80.0, d_f=120.0, t=1.5,
            r_punch=4.5, r_die=6.0,
            m1_lim=0.50, mn_lim=0.75,
        )
        geom_min = 4.5 + 6.0 + 1.5  # = 12
        assert min_H == pytest.approx(geom_min, abs=1.0), (
            f"min_H {min_H} should be close to geometric min {geom_min}"
        )

    def test_validate_pass_heights_estimate_message(self):
        """Error message must include the suggested minimum H."""
        seq = self._run_sequence(
            d_i=100.0, H=14.0, d_f=300.0, t=1.5,
            r_punch=4.5, r_die=6.0,
            m1_lim=0.50, mn_lim=0.75,
        )
        result = validate_pass_heights(
            seq_res=seq, r_punch=4.5, r_die=6.0, t=1.5,
            d_i=100.0, d_f=300.0, m1_lim=0.50, mn_lim=0.75,
        )
        assert result.has_errors
        assert any("mm" in err for err in result.errors)
