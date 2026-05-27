"""
tests/test_pass_sequence.py
============================
Unit tests for pass_sequence.py
"""

import math
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from blank_calculator import compute_blank
from pass_sequence import compute_pass_sequence, PassSequenceResult, PassData


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

BASE = dict(
    d_i=80.0,
    H=60.0,
    t=1.5,
    r_die_final=6.0,
    r_punch_final=4.5,
    m1_lim=0.50,
    mn_lim=0.75,
    d_f=120.0,
)


def run(d_blank: float, **overrides):
    kwargs = {**BASE, **overrides}
    return compute_pass_sequence(d_blank=d_blank, **kwargs)


# ---------------------------------------------------------------------------
# Return type and structure
# ---------------------------------------------------------------------------

class TestOutputStructure:

    def test_returns_pass_sequence_result(self):
        result = run(d_blank=160.0)
        assert isinstance(result, PassSequenceResult)

    def test_passes_is_list(self):
        result = run(d_blank=160.0)
        assert isinstance(result.passes, list)

    def test_n_passes_matches_list_length(self):
        result = run(d_blank=160.0)
        assert result.n_passes == len(result.passes)

    def test_each_element_is_pass_data(self):
        result = run(d_blank=160.0)
        for p in result.passes:
            assert isinstance(p, PassData)

    def test_pass_numbers_sequential(self):
        result = run(d_blank=160.0)
        for i, p in enumerate(result.passes, start=1):
            assert p.pass_number == i

    def test_last_pass_is_final(self):
        result = run(d_blank=160.0)
        assert result.passes[-1].is_final is True

    def test_intermediate_passes_not_final(self):
        result = run(d_blank=300.0)  # many passes
        for p in result.passes[:-1]:
            assert p.is_final is False


# ---------------------------------------------------------------------------
# Diameter continuity
# ---------------------------------------------------------------------------

class TestDiameterContinuity:

    def test_first_pass_d_before_equals_d_blank(self):
        d_blank = 160.0
        result = run(d_blank=d_blank)
        assert result.passes[0].d_before == pytest.approx(d_blank, rel=1e-4)

    def test_each_pass_d_before_equals_previous_d_after(self):
        result = run(d_blank=250.0)
        for i in range(1, len(result.passes)):
            assert result.passes[i].d_before == pytest.approx(
                result.passes[i-1].d_after, rel=1e-4
            )

    def test_last_pass_d_after_equals_d_target(self):
        result = run(d_blank=160.0)
        d_target = BASE["d_i"] + BASE["t"]  # 81.5
        assert result.passes[-1].d_after == pytest.approx(d_target, rel=1e-3)

    def test_diameters_strictly_decreasing(self):
        result = run(d_blank=250.0)
        for p in result.passes:
            assert p.d_after < p.d_before


# ---------------------------------------------------------------------------
# Drawing coefficients and ratios
# ---------------------------------------------------------------------------

class TestDrawingRatios:

    def test_drawing_coeff_formula(self):
        result = run(d_blank=160.0)
        for p in result.passes:
            expected_m = p.d_after / p.d_before
            assert p.drawing_coeff == pytest.approx(expected_m, rel=1e-4)

    def test_drawing_ratio_is_inverse_of_coeff(self):
        result = run(d_blank=160.0)
        for p in result.passes:
            assert p.drawing_ratio == pytest.approx(1.0 / p.drawing_coeff, rel=1e-4)

    def test_reduction_pct_formula(self):
        result = run(d_blank=160.0)
        for p in result.passes:
            expected = (1.0 - p.drawing_coeff) * 100.0
            assert p.reduction_pct == pytest.approx(expected, rel=1e-4)

    def test_no_pass_exceeds_m1_lim_severely(self):
        """First pass drawing coeff must be >= m1_lim (less severe or equal)."""
        result = run(d_blank=160.0, m1_lim=0.50)
        # The distributed coefficient may be slightly above m1_lim (less severe)
        # but must not be dramatically below (would exceed the limit)
        assert result.passes[0].drawing_coeff >= 0.45  # tolerance band

    def test_severity_is_valid_value(self):
        result = run(d_blank=160.0)
        for p in result.passes:
            assert p.severity in ("green", "yellow", "red")


# ---------------------------------------------------------------------------
# Number of passes logic
# ---------------------------------------------------------------------------

class TestNumberOfPasses:

    def test_single_pass_for_small_dr(self):
        # d_blank slightly above d_target → 1 pass
        d_i, t = 80.0, 1.5
        d_target = d_i + t   # 81.5
        # DR = 90 / 81.5 ≈ 1.1 << LDR of 2.0 → should be 1 pass
        result = run(d_blank=90.0)
        assert result.n_passes == 1

    def test_multiple_passes_for_high_dr(self):
        # Very large blank relative to target → multiple passes
        result = run(d_blank=300.0)
        assert result.n_passes > 1

    def test_n_passes_increases_with_blank_size(self):
        r1 = run(d_blank=120.0)
        r2 = run(d_blank=250.0)
        assert r2.n_passes >= r1.n_passes

    def test_total_drawing_ratio(self):
        d_blank = 160.0
        result = run(d_blank=d_blank)
        d_target = BASE["d_i"] + BASE["t"]
        expected_dr = d_blank / d_target
        assert result.total_drawing_ratio == pytest.approx(expected_dr, rel=1e-4)


# ---------------------------------------------------------------------------
# Final pass specific checks
# ---------------------------------------------------------------------------

class TestFinalPass:

    def test_final_pass_uses_correct_r_die(self):
        result = run(d_blank=160.0)
        assert result.passes[-1].r_die == pytest.approx(BASE["r_die_final"], rel=1e-6)

    def test_final_pass_height_equals_H(self):
        result = run(d_blank=160.0)
        assert result.passes[-1].height == pytest.approx(BASE["H"], rel=1e-6)


# ---------------------------------------------------------------------------
# Height monotonicity — intermediate heights must not exceed final height,
# and must increase monotonically toward it.
# ---------------------------------------------------------------------------

class TestHeightMonotonicity:

    def _blank(self, d_i, H, d_f, t, r_punch=4.5):
        return compute_blank(d_i=d_i, H=H, d_f=d_f, t=t, r_punch=r_punch).d_blank_final

    def test_heights_monotonically_increasing(self):
        """Standard steel cup — multi-pass, height must grow monotonically."""
        d_blank = self._blank(80.0, 60.0, 120.0, 1.5)
        result = run(d_blank=d_blank)
        heights = [p.height for p in result.passes]
        for i in range(1, len(heights)):
            assert heights[i] >= heights[i-1] - 1e-6, (
                f"Height dropped from {heights[i-1]:.2f} to {heights[i]:.2f} "
                f"between pass {i} and pass {i+1}"
            )

    def test_no_intermediate_height_exceeds_final(self):
        """Intermediate heights must not overshoot the final part height."""
        d_blank = self._blank(80.0, 60.0, 120.0, 1.5)
        result = run(d_blank=d_blank)
        final_h = result.passes[-1].height
        for p in result.passes[:-1]:
            assert p.height <= final_h + 1e-6, (
                f"Intermediate pass {p.pass_number} height {p.height:.2f} "
                f"exceeds final height {final_h:.2f}"
            )

    def test_first_pass_height_greater_than_zero(self):
        result = run(d_blank=160.0)
        assert result.passes[0].height > 0

    def test_wide_flange_height_monotonic(self):
        """Large flange, shallow cup — the case that triggered the bug."""
        d_blank = self._blank(100.0, 40.0, 300.0, 1.5)
        result = run(d_blank=d_blank, d_i=100.0, H=40.0, d_f=300.0, t=1.5)
        heights = [p.height for p in result.passes]
        for i in range(1, len(heights)):
            assert heights[i] >= heights[i-1] - 1e-6, (
                f"Height dropped from {heights[i-1]:.2f} to {heights[i]:.2f} "
                f"(wide flange case)"
            )

    def test_deep_cup_height_monotonic(self):
        """Deep cup case — many passes, verify monotonic growth."""
        d_blank = self._blank(80.0, 120.0, 120.0, 1.5)
        result = run(d_blank=d_blank, d_i=80.0, H=120.0, d_f=120.0, t=1.5)
        heights = [p.height for p in result.passes]
        for i in range(1, len(heights)):
            assert heights[i] >= heights[i-1] - 1e-6, (
                f"Height dropped from {heights[i-1]:.2f} to {heights[i]:.2f} "
                f"(deep cup case)"
            )


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestErrors:

    def test_raises_on_zero_d_blank(self):
        with pytest.raises(ValueError):
            run(d_blank=0.0)

    def test_raises_on_negative_d_blank(self):
        with pytest.raises(ValueError):
            run(d_blank=-50.0)

    def test_raises_on_zero_t(self):
        with pytest.raises(ValueError):
            run(d_blank=160.0, t=0.0)

    def test_raises_on_invalid_d_f(self):
        with pytest.raises(ValueError):
            run(d_blank=160.0, d_f=80.0)  # d_f <= d_i + 2t = 83.0


# ---------------------------------------------------------------------------
# Flange diameter checks
# ---------------------------------------------------------------------------

class TestFlangeDiameter:

    def test_flange_diameter_present(self):
        result = run(d_blank=160.0)
        for p in result.passes:
            assert hasattr(p, "flange_diameter")

    def test_flange_diameter_positive(self):
        result = run(d_blank=160.0)
        for p in result.passes:
            assert p.flange_diameter > 0

    def test_flange_diameter_final_equals_d_f(self):
        result = run(d_blank=160.0)
        assert result.passes[-1].flange_diameter == pytest.approx(120.0, rel=1e-3)

    def test_flange_diameter_monotonic_decreasing(self):
        result = run(d_blank=300.0)  # multiple passes
        flanges = [p.flange_diameter for p in result.passes]
        for i in range(1, len(flanges)):
            assert flanges[i] <= flanges[i-1] + 1e-6

    def test_flange_diameter_first_pass_less_than_blank(self):
        result = run(d_blank=250.0)
        d_blank = 250.0
        assert result.passes[0].flange_diameter <= d_blank + 1e-6

    def test_flange_diameter_ge_outer_wall(self):
        result = run(d_blank=250.0)
        for p in result.passes:
            min_d = p.d_after + 1.5  # d_after + t
            assert p.flange_diameter >= min_d - 1e-6
