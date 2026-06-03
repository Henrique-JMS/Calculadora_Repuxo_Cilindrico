"""
app.py
======
Streamlit web interface for the Cylindrical Deep Drawing Calculator.

Layout:
    Sidebar  — all user inputs (geometry, material, advanced parameters)
    Main     — results summary cards, severity gauges, pass table,
               per-stage drawings, DXF download

Run locally:
    streamlit run app.py

References:
    - PRD §8 — Interface Streamlit
"""

from __future__ import annotations

import hashlib
import io
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import streamlit as st

from blank_calculator import compute_blank as _compute_blank
from constants import DEFAULT_SAFETY_FACTOR, DEFAULT_TRIM_ALLOWANCE
from dxf_generator import generate_dxf_bytes
from materials import (
    CUSTOM_KEY,
    build_custom_material,
    get_material,
    list_material_names,
)
from pass_sequence import compute_pass_sequence as _compute_pass_sequence
from precache import inputs_are_default, load_cache as _load_cache
from process_data import compute_process_data as _compute_process_data
from gif_renderer import generate_animation_gif as _generate_animation_gif
from renderer import render_all_stages, render_final_part_full, render_overview
from validators import validate_inputs, validate_pass_heights

# ---------------------------------------------------------------------------
# Page configuration
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Calculadora de Repuxo Cilíndrico",
    page_icon="🔩",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Streamlit-cached wrappers — avoid redundant recomputation on widget changes
compute_blank = st.cache_data(_compute_blank)
compute_pass_sequence = st.cache_data(_compute_pass_sequence)
compute_process_data = st.cache_data(_compute_process_data)
generate_gif = st.cache_data(_generate_animation_gif)

# ---------------------------------------------------------------------------
# Custom CSS
# ---------------------------------------------------------------------------

st.markdown("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Roboto+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
    * { font-family: 'Inter', system-ui, -apple-system, sans-serif; }
    code, pre, .mono { font-family: 'Roboto Mono', 'Cascadia Code', Consolas, monospace; }

    /* Sidebar */
    section[data-testid="stSidebar"] { padding-top: 1rem; }
    section[data-testid="stSidebar"] h3 {
        font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.06em;
        color: #5A9FD4; margin-top: 1.5rem; border-left: 3px solid #5A9FD4;
        padding-left: 0.6rem;
    }
    section[data-testid="stSidebar"] .stInfo {
        font-size: 0.85rem;
    }

    /* Metric cards */
    div[data-testid="metric-container"] {
        border: 1px solid rgba(128, 128, 128, 0.18);
        border-radius: 10px;
        padding: 0.6rem 0.8rem;
        background: rgba(128, 128, 128, 0.03);
        box-shadow: 0 1px 4px rgba(0,0,0,0.05);
        transition: box-shadow 0.2s ease, transform 0.2s ease;
    }
    div[data-testid="metric-container"]:hover {
        box-shadow: 0 3px 12px rgba(0,0,0,0.09);
        transform: translateY(-1px);
    }

    /* Buttons */
    .stButton button {
        transition: all 0.2s ease;
        border-radius: 8px;
        font-weight: 500;
    }
    .stButton button:hover {
        transform: translateY(-1px);
        box-shadow: 0 2px 8px rgba(0,0,0,0.10);
    }
    button[kind="primary"] { font-weight: 600; }

    /* Section headers */
    .section-header {
        font-size: 1.05rem; font-weight: 700;
        color: #5A9FD4; margin: 1.4rem 0 0.6rem 0;
        border-bottom: 2px solid rgba(90, 159, 212, 0.3);
        padding-bottom: 4px;
        letter-spacing: 0.01em;
    }

    /* Severity gauge bar */
    .gauge-wrapper {
        display: flex; align-items: center; gap: 0.5rem;
        width: 100%;
    }
    .gauge-track {
        flex: 1; height: 7px; background: rgba(128,128,128,0.10);
        border-radius: 4px; overflow: hidden;
    }
    .gauge-bar {
        height: 100%; border-radius: 4px;
        transition: width 0.4s ease;
        min-width: 4px;
    }
    .gauge-label {
        font-weight: 600; font-size: 0.88rem;
        white-space: nowrap; min-width: 5rem;
        font-family: 'Roboto Mono', monospace;
    }
    .gauge-label-green  { color: #2E7D32; }
    .gauge-label-yellow { color: #F57F17; }
    .gauge-label-red    { color: #D32F2F; }

    /* Empty state card */
    .empty-state {
        text-align: center; padding: 2.5rem 1.5rem;
        border: 1px dashed rgba(128,128,128,0.25);
        border-radius: 12px;
        background: rgba(128,128,128,0.02);
        margin: 1rem 0;
    }
    .empty-state-icon {
        font-size: 2.5rem; margin-bottom: 1rem;
    }
    .empty-state h4 {
        color: #5A9FD4; font-weight: 600; margin: 0 0 0.5rem 0;
    }

    /* Footer */
    .footer {
        text-align: center; font-size: 0.78rem;
        color: rgba(128,128,128,0.55);
        padding: 1rem 0 0.5rem 0;
    }
    .footer a { color: #5A9FD4; text-decoration: none; }

    /* Dataframe */
    .stDataFrame { border-radius: 8px; overflow: hidden; }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Helper: severity badge HTML
# ---------------------------------------------------------------------------

def _gauge_bar(severity: str, value: str) -> str:
    colors = {"green": "#4CAF50", "yellow": "#FFC107", "red": "#F44336"}
    widths = {"green": "30%", "yellow": "60%", "red": "90%"}
    color = colors.get(severity, "#999")
    w = widths.get(severity, "50%")
    cls = f"gauge-label-{severity}"
    return (
        f'<div class="gauge-wrapper">'
        f'  <div class="gauge-track">'
        f'    <div class="gauge-bar" style="width:{w};background:{color};"></div>'
        f'  </div>'
        f'  <span class="gauge-label {cls}">{value}</span>'
        f'</div>'
    )


def _section(title: str) -> None:
    st.markdown(f'<div class="section-header">{title}</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Float input helper — text_input that returns a validated float
# ---------------------------------------------------------------------------

def _float_input(
    container,
    label: str,
    value: float,
    min_value: float,
    max_value: float,
    step: float,
    format_str: str,
    help: str | None = None,
) -> float:
    """
    Sidebar-friendly float input without spinner or scroll-capture.

    Uses st.text_input internally, parses and validates the result.
    On invalid input (parse error, out of range) the previous valid
    *value* is returned silently.
    """
    s = container.text_input(label, value=format_str % value, help=help)
    try:
        v = float(s.replace(",", "."))
    except ValueError:
        return value
    if v < min_value or v > max_value:
        return value
    return v


# ---------------------------------------------------------------------------
# Sidebar — inputs
# ---------------------------------------------------------------------------

def _build_sidebar() -> dict:
    """Render all sidebar widgets and return a dict of input values."""

    st.sidebar.title("Parâmetros de Entrada")
    calc_btn = st.sidebar.button("Calcular", type="primary", use_container_width=True)
    st.sidebar.markdown("---")

    # ---- Geometry ----------------------------------------------------------
    st.sidebar.markdown("### 📐 Dimensões da Peça Final")

    d_i = _float_input(
        st.sidebar, "Diâmetro interno d (mm)",
        60.0, 1.0, 2000.0, 0.5, "%.1f",
        help="Diâmetro interno do cilindro acabado, medido pela superfície interna."
    )
    H = _float_input(
        st.sidebar, "Altura da parede H (mm)",
        50.0, 0.1, 2000.0, 0.5, "%.1f",
        help="Altura da parede cilíndrica — do fundo interno até a base da aba."
    )
    d_f = _float_input(
        st.sidebar, "Diâmetro da aba (flange) Da (mm)",
        120.0, 1.0, 3000.0, 0.5, "%.1f",
        help="Diâmetro externo da aba plana. Deve ser maior que d + 2e."
    )
    t = _float_input(
        st.sidebar, "Espessura da chapa e (mm)",
        1.5, 0.1, 20.0, 0.1, "%.2f",
        help="Espessura nominal da chapa metálica (blank)."
    )

    # Auto-suggest radii based on t
    r_die_default   = round(max(4.0 * t, 3.0), 1)
    r_punch_default = round(max(3.0 * t, 2.0), 1)

    r_die = _float_input(
        st.sidebar, "Raio da matriz Rm (mm)",
        r_die_default, 0.1, 100.0, 0.1, "%.1f",
        help=f"Raio de concordância da borda da matriz. Mínimo recomendado: 4e = {4*t:.1f} mm."
    )
    r_punch = _float_input(
        st.sidebar, "Raio do punção Rp (mm)",
        r_punch_default, 0.1, 100.0, 0.1, "%.1f",
        help=f"Raio de concordância do punção (fundo–parede). Mínimo recomendado: 3e = {3*t:.1f} mm."
    )

    # ---- Material ----------------------------------------------------------
    st.sidebar.markdown("### 🔬 Material")

    mat_names = list_material_names()
    mat_choice = st.sidebar.selectbox(
        "Material", mat_names, index=0,
        help="Selecione um material pré-configurado ou insira os dados manualmente."
    )

    if mat_choice == CUSTOM_KEY:
        col1, col2 = st.sidebar.columns(2)
        uts = _float_input(col1, "UTS (MPa)", 310.0, 1.0, 9999.0, 5.0, "%.1f")
        ys = _float_input(col2, "Ys (MPa)", 175.0, 1.0, 9999.0, 5.0, "%.1f")
        m1_lim = st.sidebar.slider("m₁ lim (1° passe)", 0.40, 0.70, 0.50, 0.01)
        mn_lim = st.sidebar.slider("mₙ lim (passes subs.)", 0.60, 0.90, 0.75, 0.01)
    else:
        mat = get_material(mat_choice)
        uts    = mat.uts
        ys     = mat.ys
        m1_lim = mat.m1_lim
        mn_lim = mat.mn_lim
        st.sidebar.info(
            f"**UTS:** {uts:.0f} MPa  |  **Ys:** {ys:.0f} MPa\n\n"
            f"**m₁:** {m1_lim:.2f}  |  **mₙ:** {mn_lim:.2f}  |  **µ:** {mat.mu:.2f}"
        )

    # ---- Advanced ----------------------------------------------------------
    with st.sidebar.expander("🔧 Parâmetros Avançados", expanded=False):
        trim_pct = st.slider(
            "Margem de apara (%)", 0, 10, int(DEFAULT_TRIM_ALLOWANCE * 100), 1,
            help="Adicional ao blank para compensar irregularidades de borda (earing)."
        )
        safety_factor = st.slider(
            "Fator de segurança (prensa)", 1.00, 2.00, DEFAULT_SAFETY_FACTOR, 0.05,
            help="Multiplicador aplicado sobre a força total para dimensionar a prensa."
        )

    return dict(
        d_i=d_i, H=H, d_f=d_f, t=t,
        r_die=r_die, r_punch=r_punch,
        uts=uts, ys=ys, m1_lim=m1_lim, mn_lim=mn_lim,
        mat_choice=mat_choice,
        trim_fraction=trim_pct / 100.0,
        safety_factor=safety_factor,
        calc_btn=calc_btn,
    )


# ---------------------------------------------------------------------------
# Result sections
# ---------------------------------------------------------------------------

def _show_summary(blank, seq, proc) -> None:
    """Top-row metric cards."""
    _section("📊 Resumo do Processo")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Ø Blank", f"{blank.d_blank_final:.1f} mm",
              help="Diâmetro final do blank (com margem de apara)")
    c2.metric("N° de Passes", str(seq.n_passes),
              help="Número mínimo de etapas de conformação necessárias")
    c3.metric("DR Total", f"{seq.total_drawing_ratio:.2f}",
              help="Razão de repuxo total = D_blank / d_neutro")
    c4.metric("Prensa Mínima", f"{proc.peak_press_kN:.1f} kN",
              help="Capacidade mínima da prensa (maior dentre todos os passes)")
    c5.metric("t/D Blank", f"{blank.t_D_ratio_pct:.2f}%",
              help="Relação espessura/diâmetro — indicador de risco de rugas")


def _show_severity(sev, blank) -> None:
    """Severity indicator gauges."""
    _section("🚦 Indicadores de Severidade")
    cols = st.columns(4)

    indicators = [
        ("t/D (%)",      f"{blank.t_D_ratio_pct:.2f}%", blank.severity),
        ("DR (1° passe)", f"{sev.DR_first:.3f}",          sev.severity_DR),
        ("df/d",          f"{sev.df_d_ratio:.2f}",         sev.severity_df_d),
        ("H/d",           f"{sev.H_d_ratio:.2f}",           sev.severity_H_d),
    ]
    descriptions = [
        "Relação espessura/blank. Verde > 1.5%, vermelho < 0.5%.",
        "Razão de repuxo do 1° passe. Verde ≤ 1.8, vermelho > 2.0.",
        "Relação aba/diâmetro. Verde ≤ 1.5, vermelho > 2.0.",
        "Relação altura/diâmetro. Verde ≤ 0.5, vermelho > 1.0 (deep drawing severo).",
    ]

    for col, (label, value, severity), desc in zip(cols, indicators, descriptions):
        with col:
            st.markdown(f"**{label}**", help=desc)
            st.markdown(_gauge_bar(severity, value), unsafe_allow_html=True)


def _show_blank_detail(blank, t) -> None:
    """Blank breakdown table."""
    _section("⬜ Detalhamento do Blank")
    col_b, col_a = st.columns([1, 1])
    with col_b:
        st.markdown("**Dimensões do Blank**")
        st.markdown(f"""
| Parâmetro | Valor |
|---|---|
| Ø Teórico | {blank.d_blank_theoretical:.2f} mm |
| Margem de apara | {blank.trim_allowance_mm:.2f} mm ({blank.trim_fraction*100:.1f}%) |
| **Ø Final** | **{blank.d_blank_final:.2f} mm** |
| Espessura | {t:.2f} mm |
""")
    with col_a:
        st.markdown("**Decomposição de Área Superficial**")
        st.markdown(f"""
| Segmento | Área (mm²) |
|---|---|
| Fundo plano | {blank.area_bottom:.1f} |
| Concordância punção | {blank.area_fillet:.1f} |
| Parede cilíndrica | {blank.area_wall:.1f} |
| Aba plana | {blank.area_flange:.1f} |
| **Total peça** | **{blank.area_total_part:.1f}** |
| Blank (com apara) | {blank.area_blank:.1f} |
""")


def _show_passes_table(seq, proc) -> None:
    """Full pass sequence table with forces."""
    _section("📋 Sequência de Passes")

    import pandas as pd

    rows = []
    for pd_geom, pd_force in zip(seq.passes, proc.passes):
        sev_icon = {"green": "🟢", "yellow": "🟡", "red": "🔴"}.get(pd_geom.severity, "")
        rows.append({
            "Passe": pd_geom.pass_number,
            "Ø antes (mm)": f"{pd_geom.d_before * 2:.2f}",
            "Ø depois (mm)": f"{pd_geom.d_after * 2:.2f}",
            "Altura (mm)": f"{pd_geom.height:.2f}",
            "DR": f"{pd_geom.drawing_ratio:.3f}",
            "m": f"{pd_geom.drawing_coeff:.3f}",
            "Redução (%)": f"{pd_geom.reduction_pct:.1f}",
            "F_punch (kN)": f"{pd_force.F_punch_kN:.2f}",
            "F_PC (kN)": f"{pd_force.F_blank_holder_kN:.2f}",
            "F_ext (kN)": f"{pd_force.F_extraction_kN:.2f}",
            "F_prensa (kN)": f"{pd_force.F_press_kN:.2f}",
            "F_prensa (tf)": f"{pd_force.F_press_tonf:.2f}",
            "Severidade": sev_icon,
        })

    df = pd.DataFrame(rows)

    def _row_color(s):
        sev = s.get("Severidade", "")
        if sev == "🔴":
            return ["background-color: rgba(244, 67, 54, 0.06)"] * len(s)
        elif sev == "🟡":
            return ["background-color: rgba(255, 193, 7, 0.06)"] * len(s)
        return [""] * len(s)

    styled = df.style.apply(_row_color, axis=1)
    st.dataframe(styled, width='stretch', hide_index=True)


def _show_forces_detail(proc) -> None:
    """Detailed force breakdown per pass in expander."""
    with st.expander("🔬 Detalhamento de Forças por Passe", expanded=False):
        for pf in proc.passes:
            st.markdown(f"**Passe {pf.pass_number}**")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Força de Repuxo", f"{pf.F_punch_kN:.2f} kN")
            c2.metric("Força Prensa-Chapas", f"{pf.F_blank_holder_kN:.2f} kN")
            c3.metric("Força de Extração", f"{pf.F_extraction_kN:.2f} kN")
            c4.metric("Capacidade Prensa", f"{pf.F_press_tonf:.2f} tf")
            st.markdown(
                f"Área de contato BH: **{pf.A_blank_holder_mm2:.1f} mm²**  |  "
                f"Pressão BH: **{pf.p_blank_holder_MPa:.3f} MPa**  |  "
                f"Energia/ciclo: **{pf.energy_J:.1f} J**"
            )
            st.markdown("---")


def _show_drawings(blank_res, seq_res, t, d_f, d_i) -> None:
    """Per-stage drawing figures in tabs."""
    _section("📐 Desenhos por Etapa")

    stage_labels = ["Blank"] + [
        f"Passe {p.pass_number}" + (" (Final)" if p.is_final else "")
        for p in seq_res.passes
    ]

    figs = render_all_stages(blank_res, seq_res, t=t, d_f=d_f, d_i=d_i)

    tabs = st.tabs(stage_labels)
    for tab, fig in zip(tabs, figs):
        with tab:
            st.pyplot(fig, width='stretch')
            plt.close(fig)

    st.markdown("#### Visão Geral")
    overview = render_overview(blank_res, seq_res, t=t, d_f=d_f)
    st.pyplot(overview, width='stretch')
    plt.close(overview)


def _show_dxf_download(blank_res, seq_res, t, d_f) -> None:
    """DXF download button."""
    _section("💾 Exportar Desenho DXF")
    st.markdown(
        "O arquivo DXF contém o perfil em corte de todas as etapas, "
        "com cotas e legendas, compatível com AutoCAD, LibreCAD e FreeCAD."
    )

    with st.spinner("Gerando arquivo DXF…"):
        dxf_bytes = generate_dxf_bytes(blank_res, seq_res, t=t, d_f=d_f)

    st.download_button(
        label="⬇️  Baixar DXF — Sequência Completa",
        data=dxf_bytes,
        file_name="repuxo_cilindrico_sequencia.dxf",
        mime="application/dxf",
        width='stretch',
    )


def _show_final_part_drawing(d_i, H, d_f, t, r_punch, r_die) -> None:
    """Full mirrored cross-section drawing of the final part."""
    _section("🖼️ Vista da Peça Final")
    fig = render_final_part_full(
        d_i=d_i, H=H, d_f=d_f, t=t,
        r_punch=r_punch, r_die=r_die,
    )
    st.pyplot(fig, width='stretch')
    plt.close(fig)


def _show_animation(blank_res, seq_res, t, d_f, d_i) -> None:
    """Animated GIF of all stages (blank → final)."""
    _section("🎬 Animação do Processo")
    gif_bytes = st.session_state.pop("_precached_gif", None)
    if gif_bytes is None:
        gif_bytes = generate_gif(
            blank_res, seq_res, t=t, d_f=d_f, d_i=d_i,
        )
    st.image(gif_bytes, width='stretch')


# ---------------------------------------------------------------------------
# Glossary dialog
# ---------------------------------------------------------------------------

from pathlib import Path

_SECTIONS_TO_EXCLUDE = frozenset({
    "9. Validação",
    "11. Renderização",
    "13. Classes (Dataclasses)",
})


@st.cache_data
def _load_glossary() -> list[dict]:
    """Parse glossario.md into a list of {section, term, location, description}."""
    text = Path(__file__).parent.joinpath("glossario.md").read_text(encoding="utf-8")
    entries: list[dict] = []
    section = None
    term = None
    location = ""
    description = ""

    def _flush() -> None:
        nonlocal term, location, description
        if term:
            entries.append(dict(
                section=section, term=term,
                location=location, description=description,
            ))
        term = None
        location = ""
        description = ""

    for line in text.splitlines():
        if line.startswith("## "):
            _flush()
            section = line.lstrip("# ")
        elif line.startswith("### "):
            _flush()
            term = line.lstrip("# ")
        elif "**Onde aparece:**" in line:
            location = line.split("**Onde aparece:**")[-1].strip()
        elif "**Descrição:**" in line:
            description = line.split("**Descrição:**")[-1].strip()
    _flush()
    return [e for e in entries if e["section"] not in _SECTIONS_TO_EXCLUDE]


@st.dialog("📖 Glossário Técnico", width="large")
def _glossary_dialog() -> None:
    query = st.text_input(
        "🔍  Pesquisar termo...",
        placeholder="Ex: força, blank, matriz, repuxo...",
    ).strip().lower()

    entries = _load_glossary()

    if query:
        filtered = [
            e for e in entries
            if query in e["term"].lower()
            or query in e["description"].lower()
            or query in e["section"].lower()
        ]
    else:
        filtered = entries

    sections: dict[str, list[dict]] = {}
    for e in filtered:
        sections.setdefault(e["section"], []).append(e)

    if not sections:
        st.info("Nenhum termo encontrado.")
        return

    st.markdown(f"**{len(filtered)}** termo(s) encontrado(s)  —  "
                f"{len(sections)} seção(ões)")
    st.markdown("---")

    for section_name, items in sections.items():
        st.markdown(f"### {section_name}")
        for item in items:
            st.markdown(
                f"**{item['term']}**  \n"
                f"{item['description']}"
            )
            st.markdown("---")


# ---------------------------------------------------------------------------
# Main app
# ---------------------------------------------------------------------------

def _inputs_hash(inputs: dict) -> str:
    """Hash dos inputs excluindo estados transientes de botão."""
    d = {k: v for k, v in inputs.items() if k != "calc_btn"}
    return hashlib.md5(json.dumps(d, sort_keys=True).encode()).hexdigest()


def main() -> None:
    # Header
    st.title("Calculadora de Repuxo Cilíndrico")
    st.markdown(
        "Dimensionamento completo do processo de repuxo cilíndrico com aba simples: "
        "blank, sequência de passes, forças e geração de DXF."
    )

    _, col_btn = st.columns([5, 1])
    with col_btn:
        if st.button("📖 Glossário Técnico", type="secondary"):
            _glossary_dialog()

    st.markdown("---")

    # Sidebar inputs
    inputs = _build_sidebar()

    # ---- Gate: auto-compute on first load, button-only afterwards ----------
    if "gif_auto_computed" not in st.session_state:
        st.session_state.gif_auto_computed = True
        should_compute = True
        st.session_state.last_inputs_hash = _inputs_hash(inputs)
    elif inputs["calc_btn"]:
        st.session_state.last_inputs_hash = _inputs_hash(inputs)
        should_compute = True
    else:
        if _inputs_hash(inputs) != st.session_state.get("last_inputs_hash"):
            st.session_state.last_inputs_hash = _inputs_hash(inputs)
            should_compute = False
        else:
            should_compute = st.session_state.get("has_computed", False)

    if not should_compute:
        st.markdown(
            '<div class="empty-state">'
            '<h4>Configure os parâmetros e clique em <strong>Calcular</strong></h4>'
            '<p style="color:rgba(128,128,128,0.7);">'
            'Altere as dimensões, material e parâmetros na barra lateral '
            'e pressione o botão <strong>Calcular</strong> para ver os resultados.</p>'
            '</div>',
            unsafe_allow_html=True,
        )
        from pathlib import Path
        img_path = Path(__file__).parent / "img" / "Dimensions.JPG"
        if img_path.exists():
            st.image(str(img_path), caption="Referência das dimensões de entrada",
                     use_container_width=True)
        st.stop()

    # ---- Validation --------------------------------------------------------
    validation = validate_inputs(
        d_i=inputs["d_i"], H=inputs["H"], d_f=inputs["d_f"], t=inputs["t"],
        r_die=inputs["r_die"], r_punch=inputs["r_punch"],
        uts=inputs["uts"], ys=inputs["ys"],
        m1_lim=inputs["m1_lim"], mn_lim=inputs["mn_lim"],
    )

    if validation.has_errors:
        st.error("**Erros nos parâmetros de entrada — corrija antes de prosseguir:**")
        for err in validation.errors:
            st.error(f"• {err}")
        st.stop()

    if validation.has_warnings:
        for warn in validation.warnings:
            st.warning(f"⚠️ {warn}")

    # ---- Pre-cache (skip computation when inputs match defaults) ----------
    _precache = None
    if inputs_are_default(inputs):
        _precache = _load_cache()

    # ---- Computation (cached — identical inputs skip recomputation) --------
    if _precache is not None:
        blank_res, seq_res, proc_res, gif_bytes = _precache
        st.session_state["_precached_gif"] = gif_bytes
    else:
        with st.spinner("Calculando sequência de repuxo…"):
            blank_res = compute_blank(
                d_i=inputs["d_i"], H=inputs["H"], d_f=inputs["d_f"], t=inputs["t"],
                r_punch=inputs["r_punch"], trim_fraction=inputs["trim_fraction"],
            )
            seq_res = compute_pass_sequence(
                d_blank=blank_res.d_blank_final,
                d_i=inputs["d_i"], H=inputs["H"], t=inputs["t"],
                r_die_final=inputs["r_die"], r_punch_final=inputs["r_punch"],
                m1_lim=inputs["m1_lim"], mn_lim=inputs["mn_lim"],
                d_f=inputs["d_f"],
            )

            # Validate intermediate pass heights before showing results
            height_validation = validate_pass_heights(
                seq_res=seq_res,
                r_punch=inputs["r_punch"],
                r_die=inputs["r_die"],
                t=inputs["t"],
                d_i=inputs["d_i"],
                d_f=inputs["d_f"],
                m1_lim=inputs["m1_lim"],
                mn_lim=inputs["mn_lim"],
                trim_fraction=inputs["trim_fraction"],
            )
            if height_validation.has_errors:
                for err in height_validation.errors:
                    st.error(f"• {err}")
                st.stop()

            proc_res = compute_process_data(
                passes_geom=seq_res.passes,
                d_blank=blank_res.d_blank_final,
                d_f=inputs["d_f"], H=inputs["H"], t=inputs["t"],
                uts=inputs["uts"], ys=inputs["ys"],
                safety_factor=inputs["safety_factor"],
            )

    st.session_state.has_computed = True

    # ---- Display results ---------------------------------------------------
    _show_final_part_drawing(
        d_i=inputs["d_i"], H=inputs["H"], d_f=inputs["d_f"],
        t=inputs["t"], r_punch=inputs["r_punch"], r_die=inputs["r_die"],
    )
    _show_animation(blank_res, seq_res,
                    t=inputs["t"], d_f=inputs["d_f"], d_i=inputs["d_i"])
    st.markdown("---")
    _show_summary(blank_res, seq_res, proc_res)
    st.markdown("---")
    _show_severity(proc_res.severity, blank_res)
    st.markdown("---")
    _show_blank_detail(blank_res, inputs["t"])
    st.markdown("---")
    _show_passes_table(seq_res, proc_res)
    _show_forces_detail(proc_res)
    st.markdown("---")
    _show_drawings(blank_res, seq_res,
                   t=inputs["t"], d_f=inputs["d_f"], d_i=inputs["d_i"])
    st.markdown("---")
    _show_dxf_download(blank_res, seq_res, t=inputs["t"], d_f=inputs["d_f"])

    st.markdown(
        '<div class="footer">'
        'Calculadora de Repuxo Cilíndrico <strong>v1.0</strong>  ·  '
        'Desenvolvido por <a href="https://github.com/Henrique-JMS">Henrique Souza</a>'
        '<br><small>'
        '<a href="https://polyformproject.org/licenses/noncommercial/1.0.0">PolyForm Noncommercial License 1.0.0</a>'
        '</small>'
        '</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
