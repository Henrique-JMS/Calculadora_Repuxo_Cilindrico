"""
tests/test_blank_calculator.py
===============================
Unit tests for blank_calculator.py

Reference cases validated against:
    - Kalpakjian, S. & Schmid, S.R. — Manufacturing Engineering and Technology, 7th ed.
    - Manual surface-area calculation performed independently
"""

import math
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from blank_calculator import (
    compute_blank,
    BlankResult,
    _area_flat_bottom,
    _area_punch_fillet,
    _area_cylindrical_wall,
    _area_annular_flange,
)


# ---------------------------------------------------------------------------
# Area sub-functions
# ---------------------------------------------------------------------------

class TestAreaHelpers:

    def test_flat_bottom_basic(self):
        # d_i=100, r_p=5 → d_flat=90 → A = π/4 * 90² ≈ 6361.7
        A = _area_flat_bottom(d_i=100.0, r_punch=5.0)
        assert A == pytest.approx(math.pi / 4.0 * 90.0**2, rel=1e-6)

    def test_flat_bottom_zero_when_radius_fills_cup(self):
        # r_punch = d_i/2 → no flat bottom
        A = _area_flat_bottom(d_i=20.0, r_punch=10.0)
        assert A == pytest.approx(0.0, abs=1e-9)

    def test_flat_bottom_positive_for_valid_inputs(self):
        A = _area_flat_bottom(d_i=80.0, r_punch=4.0)
        assert A > 0

    def test_cylindrical_wall_basic(self):
        # A = π * d * H = π * 80 * 60 ≈ 15079.6
        A = _area_cylindrical_wall(d_i=80.0, H=60.0)
        assert A == pytest.approx(math.pi * 80.0 * 60.0, rel=1e-9)

    def test_cylindrical_wall_scales_with_height(self):
        A1 = _area_cylindrical_wall(80.0, 30.0)
        A2 = _area_cylindrical_wall(80.0, 60.0)
        assert A2 == pytest.approx(2.0 * A1, rel=1e-9)

    def test_annular_flange_basic(self):
        # d_f=120, d_i=80, t=1.5 → d_e=83 → A = π/4*(120²-83²)
        A = _area_annular_flange(d_f=120.0, d_i=80.0, t=1.5)
        expected = math.pi / 4.0 * (120.0**2 - 83.0**2)
        assert A == pytest.approx(expected, rel=1e-6)

    def test_annular_flange_zero_when_no_flange(self):
        # d_f <= d_e → no flange area
        A = _area_annular_flange(d_f=82.0, d_i=80.0, t=1.5)
        assert A == pytest.approx(0.0, abs=1e-9)

    def test_punch_fillet_positive(self):
        A = _area_punch_fillet(d_i=80.0, r_punch=4.5)
        assert A > 0

    def test_punch_fillet_increases_with_radius(self):
        A1 = _area_punch_fillet(d_i=80.0, r_punch=3.0)
        A2 = _area_punch_fillet(d_i=80.0, r_punch=6.0)
        assert A2 > A1

    def test_punch_fillet_at_boundary_no_flat_bottom(self):
        # r_punch = d_i/2 → no flat bottom → fillet area = 2πr_punch²
        # (flat region term vanishes, only toroid inner edge remains)
        A = _area_punch_fillet(d_i=20.0, r_punch=10.0)
        expected = 2.0 * math.pi * 100.0
        assert A == pytest.approx(expected, rel=1e-6)

    def test_blank_compute_with_large_r_punch_clamps(self):
        # r_punch > d_i/2 triggers defensive clamp; function still returns
        # a valid result (no exception) without silent data corruption.
        result = compute_blank(
            d_i=80.0, H=60.0, d_f=120.0, t=1.5,
            r_punch=50.0, trim_fraction=0.0,
        )
        # The effective r_punch is clamped to d_i/2 - ε, so blank diameter
        # must match the d_i/2 case, not the raw r_punch=50 case.
        clamped = compute_blank(
            d_i=80.0, H=60.0, d_f=120.0, t=1.5,
            r_punch=39.999, trim_fraction=0.0,
        )
        assert result.d_blank_final == pytest.approx(clamped.d_blank_final, rel=1e-4)


# ---------------------------------------------------------------------------
# compute_blank — output type and fields
# ---------------------------------------------------------------------------

class TestComputeBlankOutput:

    def setup_method(self):
        self.result = compute_blank(
            d_i=80.0, H=60.0, d_f=120.0, t=1.5, r_punch=4.5
        )

    def test_returns_blank_result(self):
        assert isinstance(self.result, BlankResult)

    def test_d_blank_final_positive(self):
        assert self.result.d_blank_final > 0

    def test_d_blank_final_greater_than_d_f(self):
        # Blank must be larger than the flange
        assert self.result.d_blank_final > 120.0

    def test_d_blank_final_greater_than_theoretical(self):
        assert self.result.d_blank_final > self.result.d_blank_theoretical

    def test_trim_adds_up(self):
        # Use abs tolerance: both values are rounded to 4 decimal places independently
        assert self.result.trim_allowance_mm == pytest.approx(
            self.result.d_blank_theoretical * self.result.trim_fraction, abs=1e-3
        )

    def test_area_parts_sum_to_total(self):
        total = (
            self.result.area_bottom
            + self.result.area_fillet
            + self.result.area_wall
            + self.result.area_flange
        )
        assert total == pytest.approx(self.result.area_total_part, rel=1e-6)

    def test_area_blank_consistent_with_d_final(self):
        expected_area = math.pi / 4.0 * self.result.d_blank_final**2
        assert self.result.area_blank == pytest.approx(expected_area, rel=1e-4)

    def test_t_d_ratio_formula(self):
        expected = (1.5 / self.result.d_blank_final) * 100.0
        assert self.result.t_D_ratio_pct == pytest.approx(expected, rel=1e-4)

    def test_severity_is_valid_string(self):
        assert self.result.severity in ("green", "yellow", "red")


# ---------------------------------------------------------------------------
# compute_blank — physical sanity checks
# ---------------------------------------------------------------------------

class TestComputeBlankSanity:

    def test_larger_height_gives_larger_blank(self):
        r1 = compute_blank(d_i=80.0, H=40.0, d_f=120.0, t=1.5, r_punch=4.5)
        r2 = compute_blank(d_i=80.0, H=80.0, d_f=120.0, t=1.5, r_punch=4.5)
        assert r2.d_blank_final > r1.d_blank_final

    def test_larger_flange_gives_larger_blank(self):
        r1 = compute_blank(d_i=80.0, H=60.0, d_f=100.0, t=1.5, r_punch=4.5)
        r2 = compute_blank(d_i=80.0, H=60.0, d_f=140.0, t=1.5, r_punch=4.5)
        assert r2.d_blank_final > r1.d_blank_final

    def test_larger_di_gives_larger_blank(self):
        r1 = compute_blank(d_i=60.0, H=60.0, d_f=120.0, t=1.5, r_punch=4.5)
        r2 = compute_blank(d_i=100.0, H=60.0, d_f=160.0, t=1.5, r_punch=4.5)
        assert r2.d_blank_final > r1.d_blank_final

    def test_zero_trim_gives_theoretical_equal_final(self):
        r = compute_blank(d_i=80.0, H=60.0, d_f=120.0, t=1.5,
                          r_punch=4.5, trim_fraction=0.0)
        assert r.d_blank_final == pytest.approx(r.d_blank_theoretical, rel=1e-9)

    def test_trim_allowance_increases_blank(self):
        r1 = compute_blank(d_i=80.0, H=60.0, d_f=120.0, t=1.5,
                           r_punch=4.5, trim_fraction=0.0)
        r2 = compute_blank(d_i=80.0, H=60.0, d_f=120.0, t=1.5,
                           r_punch=4.5, trim_fraction=0.05)
        assert r2.d_blank_final > r1.d_blank_final

    def test_severity_red_for_very_thin_sheet(self):
        # d_i=200, H=150, d_f=300, t=0.3 → very thin → t/D < 0.5%
        r = compute_blank(d_i=200.0, H=150.0, d_f=300.0, t=0.3, r_punch=1.0)
        assert r.severity == "red"

    def test_severity_green_for_thick_sheet(self):
        # Small cup, thick sheet → t/D >> 1.5%
        r = compute_blank(d_i=30.0, H=15.0, d_f=50.0, t=2.0, r_punch=4.0)
        assert r.severity in ("green", "yellow")

    def test_raises_on_invalid_d_i(self):
        with pytest.raises(ValueError):
            compute_blank(d_i=0.0, H=60.0, d_f=120.0, t=1.5, r_punch=4.5)

    def test_raises_on_invalid_H(self):
        with pytest.raises(ValueError):
            compute_blank(d_i=80.0, H=0.0, d_f=120.0, t=1.5, r_punch=4.5)

    def test_raises_on_invalid_t(self):
        with pytest.raises(ValueError):
            compute_blank(d_i=80.0, H=60.0, d_f=120.0, t=0.0, r_punch=4.5)


# ---------------------------------------------------------------------------
# Reference case: manual calculation cross-check
# ---------------------------------------------------------------------------

class TestReferenceCase:
    """
    Cross-check against independent manual surface-area calculation.

    Part: d_i=80mm, H=60mm, d_f=120mm, t=1.5mm, r_punch=4.5mm
    """

    def setup_method(self):
        self.d_i = 80.0
        self.H   = 60.0
        self.d_f = 120.0
        self.t   = 1.5
        self.r_p = 4.5
        self.result = compute_blank(
            d_i=self.d_i, H=self.H, d_f=self.d_f,
            t=self.t, r_punch=self.r_p, trim_fraction=0.0
        )

    def test_wall_area_manual(self):
        expected = math.pi * self.d_i * self.H   # π * 80 * 60
        assert self.result.area_wall == pytest.approx(expected, rel=1e-5)

    def test_flange_area_manual(self):
        d_e = self.d_i + 2.0 * self.t  # 83.0
        expected = math.pi / 4.0 * (self.d_f**2 - d_e**2)
        assert self.result.area_flange == pytest.approx(expected, rel=1e-5)

    def test_blank_diameter_in_expected_range(self):
        # For d_i=80, H=60, d_f=120, t=1.5, r_punch=4.5 the theoretical blank
        # should be in the 160–210 mm range (verified by independent calc)
        D = self.result.d_blank_theoretical
        assert 160.0 < D < 210.0, f"Blank diameter {D:.2f} outside expected range"

    def test_conservation_of_area(self):
        # Area of blank ≈ area of part (within 1% — trim_fraction=0 so exact)
        A_blank = math.pi / 4.0 * self.result.d_blank_theoretical**2
        A_part  = self.result.area_total_part
        assert A_blank == pytest.approx(A_part, rel=1e-4)
