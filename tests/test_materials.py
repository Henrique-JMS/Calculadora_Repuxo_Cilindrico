"""
tests/test_materials.py
========================
Unit tests for materials.py
"""

import math
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from materials import (
    get_material,
    list_material_names,
    build_custom_material,
    CUSTOM_KEY,
    Material,
)


# ---------------------------------------------------------------------------
# list_material_names
# ---------------------------------------------------------------------------

class TestListMaterialNames:

    def test_returns_list(self):
        names = list_material_names()
        assert isinstance(names, list)

    def test_not_empty(self):
        assert len(list_material_names()) >= 6

    def test_custom_is_last(self):
        names = list_material_names()
        assert names[-1] == CUSTOM_KEY

    def test_all_entries_are_strings(self):
        for name in list_material_names():
            assert isinstance(name, str)


# ---------------------------------------------------------------------------
# get_material
# ---------------------------------------------------------------------------

class TestGetMaterial:

    def test_returns_material_instance(self):
        mat = get_material("DC01 / DC04 (Aço baixo carbono)")
        assert isinstance(mat, Material)

    def test_dc01_uts(self):
        mat = get_material("DC01 / DC04 (Aço baixo carbono)")
        assert mat.uts == pytest.approx(310.0)

    def test_dc01_ys(self):
        mat = get_material("DC01 / DC04 (Aço baixo carbono)")
        assert mat.ys == pytest.approx(175.0)

    def test_dc01_m1_lim(self):
        mat = get_material("DC01 / DC04 (Aço baixo carbono)")
        assert mat.m1_lim == pytest.approx(0.50)

    def test_dc01_mn_lim(self):
        mat = get_material("DC01 / DC04 (Aço baixo carbono)")
        assert mat.mn_lim == pytest.approx(0.75)

    def test_stainless_higher_m1(self):
        steel = get_material("DC01 / DC04 (Aço baixo carbono)")
        ss    = get_material("Aço inoxidável AISI 304")
        assert ss.m1_lim > steel.m1_lim  # stainless is harder to draw

    def test_unknown_material_raises_key_error(self):
        with pytest.raises(KeyError):
            get_material("Unobtanium XZ-9000")

    def test_custom_key_retrievable(self):
        mat = get_material(CUSTOM_KEY)
        assert mat.name == CUSTOM_KEY

    def test_all_named_materials_retrievable(self):
        for name in list_material_names():
            mat = get_material(name)
            assert mat.name == name


# ---------------------------------------------------------------------------
# Material computed properties
# ---------------------------------------------------------------------------

class TestMaterialProperties:

    def setup_method(self):
        self.mat = get_material("DC01 / DC04 (Aço baixo carbono)")

    def test_ldr_is_inverse_of_m1(self):
        assert self.mat.ldr == pytest.approx(1.0 / self.mat.m1_lim)

    def test_ldr_subsequent_is_inverse_of_mn(self):
        assert self.mat.ldr_subsequent == pytest.approx(1.0 / self.mat.mn_lim)

    def test_bh_pressure_positive(self):
        assert self.mat.bh_pressure > 0

    def test_bh_pressure_formula(self):
        from constants import BH_PRESSURE_COEFF
        expected = BH_PRESSURE_COEFF * self.mat.ys
        assert self.mat.bh_pressure == pytest.approx(expected)

    def test_clearance_increases_with_thickness(self):
        c1 = self.mat.clearance(1.0)
        c2 = self.mat.clearance(2.0)
        assert c2 > c1

    def test_clearance_always_greater_than_t(self):
        for t in [0.5, 1.0, 2.0, 3.0]:
            assert self.mat.clearance(t) > t

    def test_str_returns_name(self):
        assert str(self.mat) == self.mat.name


# ---------------------------------------------------------------------------
# build_custom_material
# ---------------------------------------------------------------------------

class TestBuildCustomMaterial:

    def test_basic_creation(self):
        mat = build_custom_material(uts=400.0, ys=200.0)
        assert isinstance(mat, Material)
        assert mat.uts == pytest.approx(400.0)
        assert mat.ys  == pytest.approx(200.0)

    def test_name_is_custom_key(self):
        mat = build_custom_material(uts=300.0, ys=150.0)
        assert mat.name == CUSTOM_KEY

    def test_uts_zero_raises(self):
        with pytest.raises(ValueError, match="UTS"):
            build_custom_material(uts=0.0, ys=100.0)

    def test_uts_negative_raises(self):
        with pytest.raises(ValueError, match="UTS"):
            build_custom_material(uts=-10.0, ys=100.0)

    def test_ys_zero_raises(self):
        with pytest.raises(ValueError, match="Yield"):
            build_custom_material(uts=300.0, ys=0.0)

    def test_ys_exceeds_uts_raises(self):
        with pytest.raises(ValueError, match="cannot exceed"):
            build_custom_material(uts=200.0, ys=250.0)

    def test_m1_lim_out_of_range_raises(self):
        with pytest.raises(ValueError, match="m1_lim"):
            build_custom_material(uts=300.0, ys=150.0, m1_lim=0.20)

    def test_mn_lim_out_of_range_raises(self):
        with pytest.raises(ValueError, match="mn_lim"):
            build_custom_material(uts=300.0, ys=150.0, mn_lim=1.10)

    def test_mn_lim_less_than_m1_lim_raises(self):
        with pytest.raises(ValueError, match="greater than m1_lim"):
            build_custom_material(uts=300.0, ys=150.0, m1_lim=0.60, mn_lim=0.58)

    def test_mu_out_of_range_raises(self):
        with pytest.raises(ValueError, match="mu"):
            build_custom_material(uts=300.0, ys=150.0, mu=0.50)

    def test_custom_coefficients(self):
        mat = build_custom_material(
            uts=500.0, ys=250.0, m1_lim=0.55, mn_lim=0.78, mu=0.10
        )
        assert mat.m1_lim == pytest.approx(0.55)
        assert mat.mn_lim == pytest.approx(0.78)
        assert mat.mu     == pytest.approx(0.10)
