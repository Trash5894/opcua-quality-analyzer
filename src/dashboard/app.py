"""
OPC UA Quality Analyzer – Streamlit Dashboard
Industrial-grade dark UI for analyzing OPC UA NodeSet2 models.
"""

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.parser.nodeset_parser import parse
from src.metrics.metric_engine import compute, MetricResult, GlobalMetrics

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="OPC UA Quality Analyzer",
    page_icon="⚙",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Syne:wght@400;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Syne', sans-serif;
    background-color: #0b0e14;
    color: #c9d1d9;
}

h1, h2, h3 {
    font-family: 'Syne', sans-serif;
    font-weight: 800;
    letter-spacing: -0.02em;
}

.metric-card {
    background: linear-gradient(135deg, #13181f 0%, #1a2030 100%);
    border: 1px solid #2a3347;
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 12px;
    position: relative;
    overflow: hidden;
}

.metric-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0;
    width: 3px; height: 100%;
    background: linear-gradient(180deg, #00d4ff, #0066ff);
}

.metric-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    color: #5b7fa6;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    margin-bottom: 4px;
}

.metric-value {
    font-family: 'JetBrains Mono', monospace;
    font-size: 32px;
    font-weight: 600;
    color: #00d4ff;
    line-height: 1;
}

.metric-value.warning { color: #f0a500; }
.metric-value.critical { color: #ff4b4b; }

.section-header {
    font-family: 'Syne', sans-serif;
    font-size: 13px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.15em;
    color: #5b7fa6;
    border-bottom: 1px solid #1e2a3a;
    padding-bottom: 8px;
    margin: 28px 0 16px;
}

.badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 20px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    font-weight: 600;
}

.badge-ok  { background: #0d2e1a; color: #3fb950; border: 1px solid #238636; }
.badge-warn { background: #2e1f00; color: #f0a500; border: 1px solid #9e6a03; }
.badge-crit { background: #2d0f0f; color: #ff4b4b; border: 1px solid #8b1a1a; }

.stSelectbox > div > div {
    background-color: #13181f !important;
    border-color: #2a3347 !important;
    color: #c9d1d9 !important;
}

.stDataFrame { font-family: 'JetBrains Mono', monospace; font-size: 12px; }

div[data-testid="stSidebar"] {
    background-color: #0d1117;
    border-right: 1px solid #1e2a3a;
}

.stButton > button {
    background: linear-gradient(135deg, #0066ff, #00d4ff);
    color: white;
    border: none;
    border-radius: 8px;
    font-family: 'Syne', sans-serif;
    font-weight: 700;
    letter-spacing: 0.05em;
    padding: 10px 24px;
    width: 100%;
}

.stButton > button:hover {
    opacity: 0.85;
    transform: translateY(-1px);
}

.hero-title {
    font-size: 42px;
    font-weight: 800;
    background: linear-gradient(135deg, #00d4ff 0%, #0066ff 60%, #7928ca 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    line-height: 1.1;
    margin-bottom: 8px;
}

.hero-sub {
    color: #5b7fa6;
    font-size: 14px;
    font-family: 'JetBrains Mono', monospace;
    margin-bottom: 32px;
}

.principle-row {
    background: #13181f;
    border: 1px solid #1e2a3a;
    border-radius: 8px;
    padding: 12px 16px;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    gap: 12px;
}
</style>
""", unsafe_allow_html=True)

# ── Helpers ───────────────────────────────────────────────────────────────────
EXAMPLES_DIR = Path(__file__).parent.parent.parent / "examples"

PLOT_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="#0d1117",
    font=dict(family="JetBrains Mono", color="#c9d1d9", size=11),
    margin=dict(l=10, r=10, t=30, b=10),
)

COLOR_SEQ = ["#00d4ff", "#0066ff", "#7928ca", "#f0a500", "#3fb950", "#ff4b4b"]

# rgba versions for fill (plotly doesn't support 8-digit hex)
COLOR_SEQ_FILL = [
    "rgba(0,212,255,0.08)",
    "rgba(0,102,255,0.08)",
    "rgba(121,40,202,0.08)",
    "rgba(240,165,0,0.08)",
    "rgba(63,185,80,0.08)",
    "rgba(255,75,75,0.08)",
]


def rating(value: int, warn: int, crit: int) -> str:
    if value >= crit:
        return "critical"
    if value >= warn:
        return "warning"
    return ""


def badge_html(value: int, warn: int, crit: int) -> str:
    if value >= crit:
        return f'<span class="badge badge-crit">⚠ {value}</span>'
    if value >= warn:
        return f'<span class="badge badge-warn">~ {value}</span>'
    return f'<span class="badge badge-ok">✓ {value}</span>'


def metric_card(label: str, value, warn: int = 99999, crit: int = 99999):
    cls = rating(int(value), warn, crit)
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value {cls}">{value}</div>
    </div>""", unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def run_analysis(path: str) -> MetricResult:
    data = parse(path)
    return compute(data, filename=Path(path).name)


def global_metrics_df(gm: GlobalMetrics) -> pd.DataFrame:
    rows = [
        ("NClass",        gm.NClass,        "Number of ObjectTypes"),
        ("NVarType",      gm.NVarType,       "Number of VariableTypes"),
        ("NMet",          gm.NMet,           "Total Methods"),
        ("NAttrTotal",    gm.NAttrTotal,     "Total Attributes (Variables)"),
        ("MaxDIT",        gm.MaxDIT,         "Maximum Inheritance Depth"),
        ("NGenH",         gm.NGenH,          "Independent Inheritance Hierarchies"),
        ("NAggH",         gm.NAggH,          "Independent Aggregation Hierarchies"),
        ("NInst",         gm.NInst,          "Internal Instances"),
        ("NInstExternal", gm.NInstExternal,  "External Instances"),
    ]
    return pd.DataFrame(rows, columns=["Metric", "Value", "Description"])


def type_metrics_df(types) -> pd.DataFrame:
    return pd.DataFrame([{
        "BrowseName": t.browse_name,
        "WMC": t.WMC, "DIT": t.DIT, "NOC": t.NOC,
        "NAttr": t.NAttr, "NComp": t.NComp,
        "NAgg": t.NAgg, "NAssoc": t.NAssoc, "NInst": t.NInst,
    } for t in types])


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="margin-bottom:24px;">
        <div style="font-family:'Syne',sans-serif;font-size:18px;font-weight:800;
                    color:#00d4ff;letter-spacing:-0.01em;">⚙ OPC UA</div>
        <div style="font-family:'Syne',sans-serif;font-size:11px;color:#5b7fa6;
                    text-transform:uppercase;letter-spacing:0.1em;">Quality Analyzer</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-header">Load NodeSet</div>', unsafe_allow_html=True)

    source = st.radio("Source", ["Upload file", "Use example"], label_visibility="collapsed")

    xml_path = None

    if source == "Upload file":
        uploaded = st.file_uploader("NodeSet2 XML", type=["xml"],
                                    label_visibility="collapsed")
        if uploaded:
            tmp = Path("/tmp") / uploaded.name
            tmp.write_bytes(uploaded.read())
            xml_path = str(tmp)
    else:
        examples = sorted(EXAMPLES_DIR.glob("*.xml"))
        if examples:
            chosen = st.selectbox(
                "Choose example",
                examples,
                format_func=lambda p: p.name,
                label_visibility="collapsed",
            )
            xml_path = str(chosen)
        else:
            st.warning("No example files found.")

    analyze = st.button("▶ Analyze")

    st.markdown('<div class="section-header">About</div>', unsafe_allow_html=True)
    st.markdown("""
    <div style="font-size:12px;color:#5b7fa6;line-height:1.7;">
    Metrics based on:<br>
    • Chidamber & Kemerer (1993)<br>
    • Genero et al. (2005)<br>
    • Lee et al. OPC UA mapping (2017)<br><br>
    <span style="color:#3fb950;">M.Sc. Thesis — A.Ch, 2025</span>
    </div>
    """, unsafe_allow_html=True)

# ── Main ──────────────────────────────────────────────────────────────────────
st.markdown('<div class="hero-title">OPC UA Quality Analyzer</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-sub">Structural quality analysis of OPC UA NodeSet2 models via UML metrics</div>',
            unsafe_allow_html=True)

if not xml_path or not analyze:
    st.markdown("""
    <div style="background:#13181f;border:1px dashed #2a3347;border-radius:16px;
                padding:48px;text-align:center;margin-top:32px;">
        <div style="font-size:48px;margin-bottom:16px;">⚙</div>
        <div style="font-family:'Syne',sans-serif;font-size:20px;font-weight:700;
                    color:#c9d1d9;margin-bottom:8px;">Load a NodeSet2 file to begin</div>
        <div style="font-size:13px;color:#5b7fa6;">
            Upload your own XML or choose one of the bundled Companion Specifications
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# ── Run analysis ──────────────────────────────────────────────────────────────
with st.spinner("Parsing and computing metrics…"):
    try:
        result = run_analysis(xml_path)
    except Exception as e:
        st.error(f"Error parsing file: {e}")
        st.stop()

gm  = result.global_metrics
ots = result.object_types
vts = result.variable_types

st.markdown(f"""
<div style="font-family:'JetBrains Mono',monospace;font-size:12px;color:#3fb950;
            margin-bottom:24px;padding:10px 16px;background:#0d2e1a;
            border-radius:8px;border:1px solid #238636;">
✓ Analysis complete — <strong>{result.filename}</strong>
&nbsp;·&nbsp; {gm.NClass} ObjectTypes &nbsp;·&nbsp; {gm.NVarType} VariableTypes
</div>
""", unsafe_allow_html=True)

# ── Tab layout ────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(
    ["📊 Overview", "🔬 Per-Type Detail", "📈 Charts", "📋 Best Practices"])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 – Overview
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.markdown('<div class="section-header">Global Metrics</div>', unsafe_allow_html=True)

    cols = st.columns(3)
    with cols[0]:
        metric_card("NClass · ObjectTypes",  gm.NClass)
        metric_card("NVarType · VariableTypes", gm.NVarType)
        metric_card("NMet · Methods",         gm.NMet)
    with cols[1]:
        metric_card("NAttrTotal · Attributes", gm.NAttrTotal)
        metric_card("MaxDIT · Max Depth",      gm.MaxDIT, warn=3, crit=5)
        metric_card("NGenH · Inherit. Hierarchies", gm.NGenH)
    with cols[2]:
        metric_card("NAggH · Aggreg. Hierarchies", gm.NAggH)
        metric_card("NInst · Internal Instances",  gm.NInst)
        metric_card("NInstExternal · Ext. Instances", gm.NInstExternal)

    st.markdown('<div class="section-header">Raw Data Export</div>', unsafe_allow_html=True)
    df_g = global_metrics_df(gm)
    st.dataframe(df_g, use_container_width=True, hide_index=True)

    csv = df_g.to_csv(index=False).encode()
    st.download_button("⬇ Download Global Metrics CSV", csv,
                       file_name=f"{result.filename}_global.csv", mime="text/csv")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 – Per-Type Detail
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    if ots:
        st.markdown('<div class="section-header">ObjectType Metrics</div>',
                    unsafe_allow_html=True)
        df_ot = type_metrics_df(ots)

        # Color-code DIT column
        def color_dit(val):
            if val >= 5:  return "color: #ff4b4b"
            if val >= 3:  return "color: #f0a500"
            return "color: #3fb950"

        styled = df_ot.style.applymap(color_dit, subset=["DIT"])
        st.dataframe(styled, use_container_width=True, hide_index=True)

        csv_ot = df_ot.to_csv(index=False).encode()
        st.download_button("⬇ Download ObjectType CSV", csv_ot,
                           file_name=f"{result.filename}_objecttypes.csv",
                           mime="text/csv")
    else:
        st.info("No ObjectTypes found in this NodeSet.")

    if vts:
        st.markdown('<div class="section-header">VariableType Metrics</div>',
                    unsafe_allow_html=True)
        df_vt = type_metrics_df(vts)
        st.dataframe(df_vt, use_container_width=True, hide_index=True)

        csv_vt = df_vt.to_csv(index=False).encode()
        st.download_button("⬇ Download VariableType CSV", csv_vt,
                           file_name=f"{result.filename}_variabletypes.csv",
                           mime="text/csv")
    else:
        st.info("No VariableTypes found in this NodeSet.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 – Charts
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    if not ots:
        st.info("No ObjectTypes to visualize.")
    else:
        df_ot = type_metrics_df(ots)
        names = [t.browse_name.split(":")[-1] for t in ots]  # strip namespace prefix

        col1, col2 = st.columns(2)

        # ── DIT Distribution ─────────────────────────────────────────────
        with col1:
            st.markdown('<div class="section-header">DIT Distribution</div>',
                        unsafe_allow_html=True)
            fig = go.Figure(go.Bar(
                x=names, y=df_ot["DIT"],
                marker_color=[
                    "#ff4b4b" if v >= 5 else "#f0a500" if v >= 3 else "#00d4ff"
                    for v in df_ot["DIT"]
                ],
                hovertemplate="%{x}<br>DIT: %{y}<extra></extra>",
            ))
            fig.update_layout(**PLOT_LAYOUT, xaxis_tickangle=-45,
                              yaxis_title="Depth of Inheritance Tree")
            st.plotly_chart(fig, use_container_width=True)

        # ── WMC Distribution ─────────────────────────────────────────────
        with col2:
            st.markdown('<div class="section-header">WMC Distribution</div>',
                        unsafe_allow_html=True)
            fig2 = go.Figure(go.Bar(
                x=names, y=df_ot["WMC"],
                marker_color="#0066ff",
                hovertemplate="%{x}<br>WMC: %{y}<extra></extra>",
            ))
            fig2.update_layout(**PLOT_LAYOUT, xaxis_tickangle=-45,
                               yaxis_title="Weighted Methods per Class")
            st.plotly_chart(fig2, use_container_width=True)

        # ── NAttr vs NComp scatter ────────────────────────────────────────
        st.markdown('<div class="section-header">Attribute Density vs Composition</div>',
                    unsafe_allow_html=True)
        fig3 = go.Figure(go.Scatter(
            x=df_ot["NComp"], y=df_ot["NAttr"],
            mode="markers+text",
            text=names,
            textposition="top center",
            textfont=dict(size=9, color="#5b7fa6"),
            marker=dict(
                size=df_ot["DIT"].apply(lambda d: max(8, d * 8)),
                color=df_ot["WMC"],
                colorscale=[[0, "#0d2e1a"], [0.5, "#0066ff"], [1, "#ff4b4b"]],
                showscale=True,
                colorbar=dict(title="WMC", tickfont=dict(color="#5b7fa6")),
                line=dict(color="#2a3347", width=1),
            ),
            hovertemplate=(
                "<b>%{text}</b><br>"
                "NComp: %{x}<br>NAttr: %{y}<br>"
                "<extra></extra>"
            ),
        ))
        fig3.update_layout(
            **PLOT_LAYOUT,
            xaxis_title="NComp (Compositions)",
            yaxis_title="NAttr (Attributes)",
            height=420,
        )
        st.plotly_chart(fig3, use_container_width=True)

        # ── Radar chart for top type ──────────────────────────────────────
        if ots:
            st.markdown('<div class="section-header">Metric Profile — Top Types by NAttr</div>',
                        unsafe_allow_html=True)
            top = df_ot.nlargest(min(5, len(df_ot)), "NAttr")
            top_names = [n.split(":")[-1] for n in top["BrowseName"]]
            radar_metrics = ["WMC", "DIT", "NOC", "NAttr", "NComp", "NAgg"]

            fig4 = go.Figure()
            for i, (_, row) in enumerate(top.iterrows()):
                vals = [row[m] for m in radar_metrics]
                fig4.add_trace(go.Scatterpolar(
                    r=vals + [vals[0]],
                    theta=radar_metrics + [radar_metrics[0]],
                    name=top_names[i],
                    line=dict(color=COLOR_SEQ[i % len(COLOR_SEQ)], width=2),
                    fill="toself",
                    fillcolor=COLOR_SEQ_FILL[i % len(COLOR_SEQ_FILL)],
                ))
            fig4.update_layout(
                **PLOT_LAYOUT,
                polar=dict(
                    bgcolor="#0d1117",
                    radialaxis=dict(visible=True, color="#2a3347"),
                    angularaxis=dict(color="#5b7fa6"),
                ),
                height=420,
            )
            st.plotly_chart(fig4, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 – Best Practices
# ══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.markdown('<div class="section-header">OPC UA Modeling Best Practices Assessment</div>',
                unsafe_allow_html=True)
    st.markdown("""
    <div style="font-size:12px;color:#5b7fa6;margin-bottom:20px;">
    Heuristic evaluation based on OPC Foundation UA Modeling Best Practices Whitepaper (v1.03.01, 2025).
    Thresholds are relative — no absolute values are defined in the literature.
    </div>
    """, unsafe_allow_html=True)

    principles = [
        {
            "name": "Keep Inheritance Shallow",
            "desc": "DIT should remain low. Deep hierarchies reduce maintainability.",
            "metrics": f"MaxDIT = {gm.MaxDIT}",
            "status": "critical" if gm.MaxDIT >= 5 else "warning" if gm.MaxDIT >= 3 else "ok",
            "hint": "✓ Flat hierarchy" if gm.MaxDIT < 3
                    else f"⚠ MaxDIT={gm.MaxDIT} — consider flattening"
                    if gm.MaxDIT < 5 else f"⚠ MaxDIT={gm.MaxDIT} — hierarchy is deep",
        },
        {
            "name": "Prefer Composition over Inheritance",
            "desc": "Use HasComponent / HasProperty instead of deep HasSubtype chains.",
            "metrics": f"NAggH = {gm.NAggH}  ·  NGenH = {gm.NGenH}",
            "status": "ok" if gm.NAggH >= gm.NGenH else "warning",
            "hint": "✓ Composition dominates" if gm.NAggH >= gm.NGenH
                    else "⚠ Inheritance hierarchies outnumber aggregation hierarchies",
        },
        {
            "name": "Limit Complexity & Granularity",
            "desc": "Avoid overloading types with too many attributes or methods.",
            "metrics": f"NMet = {gm.NMet}  ·  NAttrTotal = {gm.NAttrTotal}",
            "status": "warning" if gm.NMet > 50 or gm.NAttrTotal > 500 else "ok",
            "hint": "✓ Complexity within range" if gm.NMet <= 50 and gm.NAttrTotal <= 500
                    else "⚠ High method or attribute count — check individual types",
        },
        {
            "name": "Reuse Types Only When Warranted",
            "desc": "Types should be instantiated. Unused type definitions add noise.",
            "metrics": f"NClass = {gm.NClass}  ·  NInst = {gm.NInst}",
            "status": "ok" if gm.NInst > 0 and gm.NClass > 0 and
                      (gm.NInst / gm.NClass) >= 0.3 else "warning",
            "hint": "✓ Good reuse rate" if gm.NClass > 0 and (gm.NInst / gm.NClass) >= 0.3
                    else "⚠ Many types appear unused — consider consolidation",
        },
        {
            "name": "Use Standardized Reference Types",
            "desc": "Prefer HasComponent, HasProperty, HasSubtype over custom references.",
            "metrics": f"NGenH = {gm.NGenH}  ·  NAggH = {gm.NAggH}",
            "status": "ok",
            "hint": "✓ Standard references detected in model structure",
        },
    ]

    badge_map = {
        "ok":       '<span class="badge badge-ok">✓ OK</span>',
        "warning":  '<span class="badge badge-warn">~ REVIEW</span>',
        "critical": '<span class="badge badge-crit">⚠ CRITICAL</span>',
    }

    for p in principles:
        st.markdown(f"""
        <div class="metric-card" style="margin-bottom:16px;">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                <div>
                    <div style="font-family:'Syne',sans-serif;font-weight:700;
                                font-size:15px;color:#c9d1d9;margin-bottom:4px;">
                        {p['name']}
                    </div>
                    <div style="font-size:12px;color:#5b7fa6;margin-bottom:8px;">
                        {p['desc']}
                    </div>
                    <div style="font-family:'JetBrains Mono',monospace;font-size:11px;
                                color:#00d4ff;">{p['metrics']}</div>
                    <div style="font-size:12px;color:#3fb950;margin-top:6px;">{p['hint']}</div>
                </div>
                <div>{badge_map[p['status']]}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("""
    <div style="font-size:11px;color:#2a3347;margin-top:24px;font-family:'JetBrains Mono',monospace;">
    Note: Threshold values are heuristic. No normative limits exist in current OPC UA literature.
    Empirical determination of thresholds is identified as future work (Thesis §7.3).
    </div>
    """, unsafe_allow_html=True)