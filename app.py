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

import io
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import streamlit as st

from blank_calculator import compute_blank
from constants import DEFAULT_SAFETY_FACTOR, DEFAULT_TRIM_ALLOWANCE
from dxf_generator import generate_dxf_bytes
from materials import (
    CUSTOM_KEY,
    build_custom_material,
    get_material,
    list_material_names,
)
from pass_sequence import compute_pass_sequence
from process_data import compute_process_data
from renderer import render_all_stages, render_overview
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

# ---------------------------------------------------------------------------
# Custom CSS
# ---------------------------------------------------------------------------

st.markdown("""
<style>
    /* Tighten sidebar padding */
    section[data-testid="stSidebar"] { padding-top: 1rem; }

    /* Metric cards */
    div[data-testid="metric-container"] {
        background: #F0F4F8;
        border: 1px solid #D0DCE8;
        border-radius: 8px;
        padding: 0.5rem 0.8rem;
    }

    /* Severity badge colours */
    .badge-green  { background:#E8F5E9; color:#1B5E20;
                    border:1px solid #A5D6A7; border-radius:6px;
                    padding:3px 10px; font-weight:600; }
    .badge-yellow { background:#FFF8E1; color:#7D5100;
                    border:1px solid #FFE082; border-radius:6px;
                    padding:3px 10px; font-weight:600; }
    .badge-red    { background:#FFEBEE; color:#B71C1C;
                    border:1px solid #EF9A9A; border-radius:6px;
                    padding:3px 10px; font-weight:600; }

    /* Section headers */
    .section-header {
        font-size: 1.05rem; font-weight: 700;
        color: #1B3A6B; margin: 1.2rem 0 0.4rem 0;
        border-bottom: 2px solid #2E6DAD; padding-bottom: 3px;
    }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Helper: severity badge HTML
# ---------------------------------------------------------------------------

def _badge(severity: str, label: str) -> str:
    cls = f"badge-{severity}"
    icons = {"green": "✅", "yellow": "⚠️", "red": "🔴"}
    icon = icons.get(severity, "")
    return f'<span class="{cls}">{icon} {label}</span>'


def _section(title: str) -> None:
    st.markdown(f'<div class="section-header">{title}</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Sidebar — inputs
# ---------------------------------------------------------------------------

def _build_sidebar() -> dict:
    """Render all sidebar widgets and return a dict of input values."""

    st.sidebar.title("⚙️ Parâmetros de Entrada")

    # ---- Geometry ----------------------------------------------------------
    st.sidebar.markdown("### 📐 Dimensões da Peça Final")

    d_i = st.sidebar.number_input(
        "Diâmetro interno d_i (mm)",
        min_value=1.0, max_value=2000.0, value=80.0, step=0.5, format="%.1f",
        help="Diâmetro interno do cilindro acabado, medido pela superfície interna."
    )
    H = st.sidebar.number_input(
        "Altura da parede H (mm)",
        min_value=0.1, max_value=2000.0, value=60.0, step=0.5, format="%.1f",
        help="Altura da parede cilíndrica — do fundo interno até a base da aba."
    )
    d_f = st.sidebar.number_input(
        "Diâmetro da aba d_f (mm)",
        min_value=1.0, max_value=3000.0, value=120.0, step=0.5, format="%.1f",
        help="Diâmetro externo da aba plana. Deve ser maior que d_i + 2t."
    )
    t = st.sidebar.number_input(
        "Espessura da chapa t (mm)",
        min_value=0.1, max_value=20.0, value=1.5, step=0.1, format="%.2f",
        help="Espessura nominal da chapa metálica (blank)."
    )

    # Auto-suggest radii based on t
    r_die_default   = round(max(4.0 * t, 3.0), 1)
    r_punch_default = round(max(3.0 * t, 2.0), 1)

    r_die = st.sidebar.number_input(
        "Raio da matriz r_die (mm)",
        min_value=0.1, max_value=100.0, value=r_die_default, step=0.1, format="%.1f",
        help=f"Raio de concordância da borda da matriz. Mínimo recomendado: 4t = {4*t:.1f} mm."
    )
    r_punch = st.sidebar.number_input(
        "Raio do punção r_punch (mm)",
        min_value=0.1, max_value=100.0, value=r_punch_default, step=0.1, format="%.1f",
        help=f"Raio de concordância do punção (fundo–parede). Mínimo recomendado: 3t = {3*t:.1f} mm."
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
        with col1:
            uts = col1.number_input("UTS (MPa)", min_value=1.0, value=310.0,
                                    step=5.0, format="%.1f")
        with col2:
            ys = col2.number_input("Ys (MPa)", min_value=1.0, value=175.0,
                                   step=5.0, format="%.1f")
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

    st.sidebar.markdown("---")
    calc_btn = st.sidebar.button("🚀 Calcular", type="primary", use_container_width=True)

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
            st.markdown(_badge(severity, value), unsafe_allow_html=True)


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
            "F_BH (kN)": f"{pd_force.F_blank_holder_kN:.2f}",
            "F_ext (kN)": f"{pd_force.F_extraction_kN:.2f}",
            "F_prensa (kN)": f"{pd_force.F_press_kN:.2f}",
            "F_prensa (tf)": f"{pd_force.F_press_tonf:.2f}",
            "Severidade": sev_icon,
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)


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
            st.pyplot(fig, use_container_width=True)
            plt.close(fig)

    st.markdown("#### Visão Geral")
    overview = render_overview(blank_res, seq_res, t=t, d_f=d_f)
    st.pyplot(overview, use_container_width=True)
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
        use_container_width=True,
    )


# ---------------------------------------------------------------------------
# Main app
# ---------------------------------------------------------------------------

def main() -> None:
    # Header
    st.title("🔩 Calculadora de Repuxo Cilíndrico")
    st.markdown(
        "Dimensionamento completo do processo de repuxo cilíndrico com aba simples: "
        "blank, sequência de passes, forças e geração de DXF."
    )
    st.markdown("---")

    # Sidebar inputs
    inputs = _build_sidebar()

    # ---- Trigger: button press OR first load with session state ------------
    if "result" not in st.session_state:
        st.session_state.result = None

    if inputs["calc_btn"]:
        st.session_state.trigger = True

    if not getattr(st.session_state, "trigger", False):
        st.info(
            "👈  Preencha os parâmetros na barra lateral e clique em **Calcular** "
            "para iniciar o dimensionamento."
        )
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

    # ---- Computation -------------------------------------------------------
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

    # ---- Display results ---------------------------------------------------
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

    st.markdown("---")
    st.caption(
        "Calculadora de Repuxo Cilíndrico • Fórmulas: Siebel, Kawai, Marciniak et al. "
        "• Desenvolvido com Python + Streamlit"
    )


if __name__ == "__main__":
    main()
