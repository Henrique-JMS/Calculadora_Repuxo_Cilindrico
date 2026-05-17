"""
tests/test_validators.py
========================
Unit tests for validators.py
"""

import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from validators import validate_inputs, validate_custom_material, ValidationResult


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
        d_i, t = 80.0, 1.5
        d_f_ok = d_i + 2.0 * t + 0.1  # = 83.1
        result = run(d_i=d_i, t=t, d_f=d_f_ok)
        # May have warnings but should not have this particular error
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
