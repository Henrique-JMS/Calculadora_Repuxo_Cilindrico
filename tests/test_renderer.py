"""
tests/test_renderer.py
=======================
Unit tests for renderer.py
"""

import math
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from blank_calculator import compute_blank
from pass_sequence import compute_pass_sequence
from renderer import (
    render_blank,
    render_pass,
    render_all_stages,
    render_overview,
    _arc_xy,
    _cup_radii,
    _blank_profile,
    _cup_profile,
    _blank_fill_polygon,
    _cup_fill_polygon,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def standard_chain():
    blank = compute_blank(d_i=80.0, H=60.0, d_f=120.0, t=1.5,
                          r_punch=4.5, trim_fraction=0.03)
    seq = compute_pass_sequence(
        d_blank=blank.d_blank_final,
        d_i=80.0, H=60.0, t=1.5,
        r_die_final=6.0, r_punch_final=4.5,
        m1_lim=0.50, mn_lim=0.75,
        d_f=120.0,
    )
    return blank, seq


# ---------------------------------------------------------------------------
# Arc helper
# ---------------------------------------------------------------------------

class TestArcXY:

    def test_returns_two_arrays(self):
        x, y = _arc_xy(0, 0, 10, 0, 90)
        assert isinstance(x, np.ndarray)
        assert isinstance(y, np.ndarray)

    def test_same_length(self):
        x, y = _arc_xy(0, 0, 10, 0, 90)
        assert len(x) == len(y)

    def test_start_point_at_0_deg(self):
        x, y = _arc_xy(cx=5, cy=3, r=10, start_deg=0, end_deg=90)
        assert x[0] == pytest.approx(5 + 10, rel=1e-6)
        assert y[0] == pytest.approx(3, abs=1e-6)

    def test_end_point_at_90_deg(self):
        x, y = _arc_xy(cx=5, cy=3, r=10, start_deg=0, end_deg=90)
        assert x[-1] == pytest.approx(5, abs=1e-4)
        assert y[-1] == pytest.approx(3 + 10, rel=1e-4)

    def test_radius_constant(self):
        cx, cy, r = 0, 0, 7
        x, y = _arc_xy(cx, cy, r, 0, 360)
        radii = np.sqrt((x - cx)**2 + (y - cy)**2)
        assert np.allclose(radii, r, rtol=1e-6)

    def test_270_to_360_punch_fillet(self):
        """Punch fillet: start at bottom (270°), end at right (360°)."""
        x, y = _arc_xy(0, 5, 5, 270, 360)
        # Start: (0 + 5*cos270°, 5 + 5*sin270°) = (0, 0)
        assert x[0] == pytest.approx(0, abs=1e-4)
        assert y[0] == pytest.approx(0, abs=1e-4)
        # End: (0 + 5*cos0°, 5 + 5*sin0°) = (5, 5)
        assert x[-1] == pytest.approx(5, abs=1e-4)
        assert y[-1] == pytest.approx(5, abs=1e-4)

    def test_wraps_when_end_less_than_start(self):
        """If end < start, arc wraps through 360° (CCW)."""
        x, y = _arc_xy(0, 0, 1, 350, 10)   # 20° of arc going through 0°
        # Should have more than 2 points
        assert len(x) > 2


# ---------------------------------------------------------------------------
# Blank profile helpers
# ---------------------------------------------------------------------------

class TestBlankProfile:

    def test_returns_list_of_segments(self):
        segs = _blank_profile(d_blank=190.0, t=1.5)
        assert isinstance(segs, list)
        assert len(segs) > 0

    def test_each_segment_is_two_arrays(self):
        for xs, ys in _blank_profile(190.0, 1.5):
            assert isinstance(xs, np.ndarray)
            assert isinstance(ys, np.ndarray)
            assert len(xs) == len(ys)

    def test_fill_polygon_closes(self):
        px, py = _blank_fill_polygon(190.0, 1.5)
        assert px[0] == pytest.approx(px[-1], abs=1e-9)
        assert py[0] == pytest.approx(py[-1], abs=1e-9)

    def test_fill_polygon_y_range(self):
        t = 1.5
        _, py = _blank_fill_polygon(190.0, t)
        assert min(py) == pytest.approx(0.0, abs=1e-9)
        assert max(py) == pytest.approx(t, rel=1e-6)

    def test_fill_polygon_x_range(self):
        d = 190.0
        px, _ = _blank_fill_polygon(d, 1.5)
        assert min(px) == pytest.approx(0.0, abs=1e-9)
        assert max(px) == pytest.approx(d / 2, rel=1e-6)


# ---------------------------------------------------------------------------
# Cup profile helpers
# ---------------------------------------------------------------------------

class TestCupProfile:

    def setup_method(self):
        self.blank = compute_blank(d_i=80.0, H=60.0, d_f=120.0, t=1.5,
                                   r_punch=4.5)
        self.seq = compute_pass_sequence(
            d_blank=self.blank.d_blank_final,
            d_i=80.0, H=60.0, t=1.5,
            r_die_final=6.0, r_punch_final=4.5,
            m1_lim=0.50, mn_lim=0.75, d_f=120.0,
        )

    def test_profile_returns_segments(self):
        pd = self.seq.passes[0]
        segs = _cup_profile(pd, t=1.5)
        assert len(segs) > 0

    def test_final_pass_profile_with_flange(self):
        pd = self.seq.passes[-1]
        segs = _cup_profile(pd, t=1.5, d_f=120.0)
        assert len(segs) > 0

    def test_fill_polygon_closes(self):
        pd = self.seq.passes[-1]
        px, py = _cup_fill_polygon(pd, t=1.5, d_f=120.0)
        assert px[0] == pytest.approx(px[-1], abs=1e-6)
        assert py[0] == pytest.approx(py[-1], abs=1e-6)

    def test_fill_polygon_y_min_is_minus_t(self):
        pd = self.seq.passes[-1]
        _, py = _cup_fill_polygon(pd, t=1.5, d_f=120.0)
        assert min(py) == pytest.approx(-1.5, abs=0.05)

    def test_fill_polygon_y_max_is_H(self):
        pd = self.seq.passes[-1]
        _, py = _cup_fill_polygon(pd, t=1.5, d_f=120.0)
        assert max(py) == pytest.approx(pd.height, abs=0.1)

    def test_fill_polygon_x_max_is_flange_radius(self):
        pd = self.seq.passes[-1]
        d_f = 120.0
        px, _ = _cup_fill_polygon(pd, t=1.5, d_f=d_f)
        assert max(px) == pytest.approx(d_f / 2, abs=1.0)


# ---------------------------------------------------------------------------
# render_blank
# ---------------------------------------------------------------------------

class TestRenderBlank:

    def test_returns_figure(self, standard_chain):
        blank, _ = standard_chain
        fig = render_blank(blank, t=1.5)
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_figure_has_axes(self, standard_chain):
        blank, _ = standard_chain
        fig = render_blank(blank, t=1.5)
        assert len(fig.axes) == 1
        plt.close(fig)

    def test_figure_has_lines(self, standard_chain):
        blank, _ = standard_chain
        fig = render_blank(blank, t=1.5)
        ax = fig.axes[0]
        assert len(ax.lines) > 0
        plt.close(fig)

    def test_figure_title_contains_blank(self, standard_chain):
        blank, _ = standard_chain
        fig = render_blank(blank, t=1.5)
        title = fig.axes[0].get_title()
        assert "blank" in title.lower() or "Blank" in title
        plt.close(fig)


# ---------------------------------------------------------------------------
# render_pass
# ---------------------------------------------------------------------------

class TestRenderPass:

    def setup_method(self):
        self.blank = compute_blank(d_i=80.0, H=60.0, d_f=120.0, t=1.5,
                                   r_punch=4.5)
        self.seq = compute_pass_sequence(
            d_blank=self.blank.d_blank_final,
            d_i=80.0, H=60.0, t=1.5,
            r_die_final=6.0, r_punch_final=4.5,
            m1_lim=0.50, mn_lim=0.75, d_f=120.0,
        )

    def test_returns_figure(self):
        pd = self.seq.passes[-1]
        fig = render_pass(pd, t=1.5, d_f=120.0, d_i=80.0)
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_intermediate_pass_no_crash(self):
        if len(self.seq.passes) > 1:
            pd = self.seq.passes[0]
            fig = render_pass(pd, t=1.5, d_f=None)
            assert isinstance(fig, plt.Figure)
            plt.close(fig)

    def test_figure_has_title_with_pass_number(self):
        pd = self.seq.passes[-1]
        fig = render_pass(pd, t=1.5, d_f=120.0)
        title = fig.axes[0].get_title()
        assert str(pd.pass_number) in title
        plt.close(fig)

    def test_final_pass_title_contains_final(self):
        pd = self.seq.passes[-1]
        fig = render_pass(pd, t=1.5, d_f=120.0)
        title = fig.axes[0].get_title()
        assert "final" in title.lower() or "Final" in title
        plt.close(fig)


# ---------------------------------------------------------------------------
# render_all_stages
# ---------------------------------------------------------------------------

class TestRenderAllStages:

    def test_returns_list(self, standard_chain):
        blank, seq = standard_chain
        figs = render_all_stages(blank, seq, t=1.5, d_f=120.0, d_i=80.0)
        assert isinstance(figs, list)
        for f in figs:
            plt.close(f)

    def test_length_is_n_passes_plus_one(self, standard_chain):
        blank, seq = standard_chain
        figs = render_all_stages(blank, seq, t=1.5, d_f=120.0, d_i=80.0)
        assert len(figs) == seq.n_passes + 1
        for f in figs:
            plt.close(f)

    def test_all_elements_are_figures(self, standard_chain):
        blank, seq = standard_chain
        figs = render_all_stages(blank, seq, t=1.5, d_f=120.0, d_i=80.0)
        for fig in figs:
            assert isinstance(fig, plt.Figure)
            plt.close(fig)

    def test_first_figure_is_blank(self, standard_chain):
        blank, seq = standard_chain
        figs = render_all_stages(blank, seq, t=1.5, d_f=120.0, d_i=80.0)
        title = figs[0].axes[0].get_title()
        assert "blank" in title.lower() or "Blank" in title
        for f in figs:
            plt.close(f)


# ---------------------------------------------------------------------------
# render_overview
# ---------------------------------------------------------------------------

class TestRenderOverview:

    def test_returns_figure(self, standard_chain):
        blank, seq = standard_chain
        fig = render_overview(blank, seq, t=1.5, d_f=120.0)
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_has_correct_number_of_subplots(self, standard_chain):
        blank, seq = standard_chain
        fig = render_overview(blank, seq, t=1.5, d_f=120.0)
        assert len(fig.axes) == seq.n_passes + 1
        plt.close(fig)


# ---------------------------------------------------------------------------
# Cleanup: ensure no figures leak between tests
# ---------------------------------------------------------------------------

def teardown_module(module):
    plt.close("all")
