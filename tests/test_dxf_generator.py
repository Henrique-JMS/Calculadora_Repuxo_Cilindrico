"""
tests/test_dxf_generator.py
============================
Unit tests for dxf_generator.py
"""

import io
import math
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import ezdxf

from blank_calculator import compute_blank
from pass_sequence import compute_pass_sequence
from dxf_generator import (
    generate_dxf,
    generate_dxf_bytes,
    _cup_radii,
    _draw_blank,
    _draw_cup,
)


# ---------------------------------------------------------------------------
# Shared fixture — standard part (2-pass example)
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


@pytest.fixture(scope="module")
def standard_doc(standard_chain):
    blank, seq = standard_chain
    return generate_dxf(blank, seq, t=1.5, d_f=120.0)


# ---------------------------------------------------------------------------
# _cup_radii helper
# ---------------------------------------------------------------------------

class TestCupRadii:

    def test_inner_radius_formula(self):
        r_i, r_o = _cup_radii(d_after=81.5, t=1.5)
        assert r_i == pytest.approx(81.5 / 2 - 1.5 / 2, rel=1e-9)

    def test_outer_radius_formula(self):
        r_i, r_o = _cup_radii(d_after=81.5, t=1.5)
        assert r_o == pytest.approx(81.5 / 2 + 1.5 / 2, rel=1e-9)

    def test_outer_minus_inner_equals_t(self):
        r_i, r_o = _cup_radii(d_after=100.0, t=2.0)
        assert (r_o - r_i) == pytest.approx(2.0, rel=1e-9)

    def test_inner_equals_di_over_2_for_final_pass(self):
        # d_after = d_i + t for the final pass
        d_i, t = 80.0, 1.5
        r_i, _ = _cup_radii(d_after=d_i + t, t=t)
        assert r_i == pytest.approx(d_i / 2, rel=1e-9)


# ---------------------------------------------------------------------------
# generate_dxf — document structure
# ---------------------------------------------------------------------------

class TestGenerateDxf:

    def test_returns_dxf_drawing(self, standard_doc):
        assert isinstance(standard_doc, ezdxf.document.Drawing)

    def test_doc_has_modelspace(self, standard_doc):
        msp = standard_doc.modelspace()
        assert msp is not None

    def test_doc_has_entities(self, standard_doc):
        msp = standard_doc.modelspace()
        entities = list(msp)
        assert len(entities) > 0

    def test_doc_has_line_entities(self, standard_doc):
        msp = standard_doc.modelspace()
        lines = [e for e in msp if e.dxftype() == "LINE"]
        assert len(lines) > 0

    def test_doc_has_arc_entities(self, standard_doc):
        msp = standard_doc.modelspace()
        arcs = [e for e in msp if e.dxftype() == "ARC"]
        assert len(arcs) > 0

    def test_doc_has_text_entities(self, standard_doc):
        msp = standard_doc.modelspace()
        texts = [e for e in msp if e.dxftype() == "TEXT"]
        assert len(texts) > 0

    def test_required_layers_exist(self, standard_doc):
        layer_names = {layer.dxf.name for layer in standard_doc.layers}
        for required in ("CONTORNO", "EIXO", "COTA", "LEGENDA"):
            assert required in layer_names, f"Layer '{required}' missing"

    def test_layer_colors(self, standard_doc):
        layers = {l.dxf.name: l for l in standard_doc.layers}
        assert layers["CONTORNO"].color == 7
        assert layers["EIXO"].color == 1
        assert layers["COTA"].color == 2
        assert layers["LEGENDA"].color == 4

    def test_units_set_to_mm(self, standard_doc):
        assert standard_doc.header["$INSUNITS"] == 4   # 4 = mm

    def test_entities_on_correct_layers(self, standard_doc):
        msp = standard_doc.modelspace()
        valid_layers = {"CONTORNO", "EIXO", "COTA", "LEGENDA", "HATCH"}
        for entity in msp:
            if hasattr(entity.dxf, "layer"):
                assert entity.dxf.layer in valid_layers, (
                    f"Entity {entity.dxftype()} on unexpected layer "
                    f"'{entity.dxf.layer}'"
                )


# ---------------------------------------------------------------------------
# generate_dxf — entity count scales with number of passes
# ---------------------------------------------------------------------------

class TestEntityScaling:

    def test_more_passes_more_entities(self):
        """A geometry that requires 2 passes should produce more entities."""
        blank1 = compute_blank(d_i=80.0, H=30.0, d_f=120.0, t=1.5, r_punch=4.5)
        seq1 = compute_pass_sequence(blank1.d_blank_final, 80.0, 30.0, 1.5,
                                      6.0, 4.5, 0.50, 0.75, d_f=120.0)

        blank2 = compute_blank(d_i=40.0, H=80.0, d_f=120.0, t=1.5, r_punch=3.0)
        seq2 = compute_pass_sequence(blank2.d_blank_final, 40.0, 80.0, 1.5,
                                      6.0, 4.5, 0.50, 0.75, d_f=120.0)

        doc1 = generate_dxf(blank1, seq1, t=1.5, d_f=120.0)
        doc2 = generate_dxf(blank2, seq2, t=1.5, d_f=120.0)

        n1 = len(list(doc1.modelspace()))
        n2 = len(list(doc2.modelspace()))

        if seq2.n_passes > seq1.n_passes:
            assert n2 > n1
        # If same number of passes, entity counts should be similar
        # (just checking no crash)

    def test_single_pass_geometry(self):
        """Small DR → single pass → document still valid."""
        blank = compute_blank(d_i=80.0, H=10.0, d_f=120.0, t=1.5, r_punch=4.5)
        seq = compute_pass_sequence(blank.d_blank_final, 80.0, 10.0, 1.5,
                                      6.0, 4.5, 0.50, 0.75, d_f=120.0)
        doc = generate_dxf(blank, seq, t=1.5, d_f=120.0)
        assert len(list(doc.modelspace())) > 0


# ---------------------------------------------------------------------------
# generate_dxf_bytes
# ---------------------------------------------------------------------------

class TestGenerateDxfBytes:

    def test_returns_bytes(self, standard_chain):
        blank, seq = standard_chain
        result = generate_dxf_bytes(blank, seq, t=1.5, d_f=120.0)
        assert isinstance(result, bytes)

    def test_bytes_not_empty(self, standard_chain):
        blank, seq = standard_chain
        result = generate_dxf_bytes(blank, seq, t=1.5, d_f=120.0)
        assert len(result) > 0

    def test_bytes_is_valid_dxf(self, standard_chain):
        """The bytes output can be re-parsed as a valid DXF document."""
        blank, seq = standard_chain
        raw = generate_dxf_bytes(blank, seq, t=1.5, d_f=120.0)
        stream = io.StringIO(raw.decode("utf-8"))
        doc = ezdxf.read(stream)
        assert doc is not None
        assert len(list(doc.modelspace())) > 0

    def test_bytes_contains_dxf_header(self, standard_chain):
        blank, seq = standard_chain
        raw = generate_dxf_bytes(blank, seq, t=1.5, d_f=120.0)
        # DXF files start with "  0\nSECTION" (group code 0, SECTION)
        text = raw.decode("utf-8")
        assert "SECTION" in text
        assert "ENTITIES" in text

    def test_bytes_roundtrip_same_entity_count(self, standard_chain):
        """Entity count must survive a bytes round-trip."""
        blank, seq = standard_chain
        doc_orig = generate_dxf(blank, seq, t=1.5, d_f=120.0)
        n_orig = len(list(doc_orig.modelspace()))

        raw = generate_dxf_bytes(blank, seq, t=1.5, d_f=120.0)
        doc_rt = ezdxf.read(io.StringIO(raw.decode("utf-8")))
        n_rt = len(list(doc_rt.modelspace()))

        assert n_rt == n_orig


# ---------------------------------------------------------------------------
# Geometric sanity checks
# ---------------------------------------------------------------------------

class TestGeometricSanity:

    def test_axis_entities_at_x0(self, standard_doc):
        """All EIXO-layer lines must pass through x = stage_axis (be vertical)."""
        msp = standard_doc.modelspace()
        eixo_lines = [e for e in msp
                      if e.dxftype() == "LINE" and e.dxf.layer == "EIXO"]
        assert len(eixo_lines) > 0
        for line in eixo_lines:
            # Axis lines are vertical: x-start == x-end
            assert abs(line.dxf.start.x - line.dxf.end.x) < 1e-6, (
                f"EIXO line not vertical: {line.dxf.start} → {line.dxf.end}"
            )

    def test_arcs_have_positive_radius(self, standard_doc):
        msp = standard_doc.modelspace()
        arcs = [e for e in msp if e.dxftype() == "ARC"]
        for arc in arcs:
            assert arc.dxf.radius > 0

    def test_contorno_lines_have_nonzero_length(self, standard_doc):
        msp = standard_doc.modelspace()
        lines = [e for e in msp
                 if e.dxftype() == "LINE" and e.dxf.layer == "CONTORNO"]
        for line in lines:
            dx = line.dxf.end.x - line.dxf.start.x
            dy = line.dxf.end.y - line.dxf.start.y
            length = math.sqrt(dx**2 + dy**2)
            assert length > 1e-6, f"Zero-length CONTORNO line found: {line.dxf}"
