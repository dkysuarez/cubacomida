"""
CubaComida — App Streamlit v2
UI/UX mejorada al mismo nivel que CubaPrecios:
- Cards en CSS Grid real (alineadas, misma altura)
- Sidebar con filtros visibles y caja de stats
- Buscador con borde claro
- Selector de orden suave y alineado
- Toda la lógica original intacta
"""

import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

# ─────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────

DB_PATH = Path(__file__).parent / "data" / "cubacomida.db"

st.set_page_config(
    page_title="CubaComida — Precios en La Habana",
    page_icon="🇨🇺",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────
# ESTILOS
# ─────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400&family=DM+Mono:wght@400;500&display=swap');

/* ── Base ── */
html, body, [class*="css"], .stApp {
    font-family: 'DM Sans', sans-serif;
    background-color: #f0f2f6 !important;
    color: #1a1a2e;
}
#MainMenu, footer, header, .stDeployButton { display: none !important; }
.block-container {
    padding-top: 1.2rem !important;
    padding-left: 2rem !important;
    padding-right: 2rem !important;
    max-width: 1340px !important;
}

/* ── SIDEBAR ── */
[data-testid="stSidebar"] {
    background-color: #ffffff !important;
    border-right: 2px solid #e2e8f0 !important;
    min-width: 290px !important;
    width: 290px !important;
}
[data-testid="stSidebarCollapseButton"] { display: none !important; }

[data-testid="stSidebar"] [data-baseweb="select"] > div:first-child {
    background-color: #f8fafc !important;
    border: 2px solid #94a3b8 !important;
    border-radius: 8px !important;
}
[data-testid="stSidebar"] [data-baseweb="select"] > div:first-child:hover {
    border-color: #475569 !important;
}
[data-testid="stSidebar"] [data-baseweb="select"] svg { color: #475569 !important; }

[data-testid="stSidebar"] .stCheckbox {
    background-color: #f8fafc;
    padding: 0.35rem 0.6rem;
    border-radius: 8px;
    border: 1px solid #e2e8f0;
}

/* ── TABS ── */
.stTabs [data-baseweb="tab-list"] {
    gap: 0;
    background: #ffffff;
    border-bottom: 2px solid #e2e8f0;
    padding: 0 0.5rem;
    margin-bottom: 1.5rem;
    border-radius: 10px 10px 0 0;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.stTabs [data-baseweb="tab"] {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.88rem;
    font-weight: 500;
    color: #64748b;
    padding: 0.75rem 1.1rem;
    border-bottom: 3px solid transparent;
    margin-bottom: -2px;
    border-radius: 0;
    background: transparent !important;
    transition: color 0.15s;
}
.stTabs [aria-selected="true"] {
    color: #1e3a5f !important;
    border-bottom: 3px solid #1e3a5f !important;
    font-weight: 700 !important;
}
.stTabs [data-baseweb="tab"]:hover { color: #1e3a5f !important; }
.stTabs [data-baseweb="tab-highlight"] { display: none; }
.stTabs [data-baseweb="tab-border"] { display: none; }

/* ── Buscador con borde visible ── */
[data-testid="stMain"] [data-testid="stTextInput"] input {
    border: 2px solid #94a3b8 !important;
    border-radius: 8px !important;
    background-color: #ffffff !important;
    padding: 0.45rem 0.75rem !important;
    font-family: 'DM Sans', sans-serif !important;
}
[data-testid="stMain"] [data-testid="stTextInput"] input:focus {
    border-color: #1e3a5f !important;
    box-shadow: 0 0 0 3px rgba(30,58,95,0.1) !important;
}

/* ── Selector orden — suave, legible ── */
[data-testid="stMain"] [data-baseweb="select"] > div:first-child {
    background-color: #f1f5f9 !important;
    border: 2px solid #94a3b8 !important;
    border-radius: 8px !important;
}
[data-testid="stMain"] [data-baseweb="select"] > div:first-child:hover {
    border-color: #475569 !important;
    background-color: #e8edf3 !important;
}
[data-testid="stMain"] [data-baseweb="select"] svg { color: #475569 !important; }
[data-testid="stMain"] [data-baseweb="select"] [data-baseweb="select-placeholder"],
[data-testid="stMain"] [data-baseweb="select"] [class*="singleValue"] {
    color: #334155 !important;
    font-weight: 600 !important;
}

/* ── Cabecera ── */
.app-titulo {
    font-size: 1.75rem;
    font-weight: 800;
    color: #1a1a2e;
    letter-spacing: -0.5px;
    line-height: 1.2;
}
.app-subtitulo {
    font-size: 0.88rem;
    color: #475569;
    font-weight: 400;
    margin-top: 3px;
    margin-bottom: 1.2rem;
}

/* ── Cards de métricas ── */
.card-metrica {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 1.1rem 1.3rem;
    margin-bottom: 1rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.03);
}
.card-valor {
    font-size: 1.85rem;
    font-weight: 700;
    color: #1a1a2e;
    font-family: 'DM Mono', monospace;
    line-height: 1.1;
}
.card-etiqueta {
    font-size: 0.72rem;
    color: #64748b;
    margin-top: 5px;
    text-transform: uppercase;
    letter-spacing: 0.9px;
    font-weight: 600;
}
.card-verde .card-valor { color: #15803d; }
.card-azul  .card-valor { color: #1d4ed8; }
.card-rojo  .card-valor { color: #dc2626; }
.card-ambar .card-valor { color: #b45309; }

/* ── Secciones ── */
.section-label {
    font-size: 0.95rem;
    font-weight: 700;
    color: #1a1a2e;
    margin-bottom: 0.1rem;
}
.section-sub {
    font-size: 0.8rem;
    color: #64748b;
    margin-bottom: 0.8rem;
}

/* ── Info box ── */
.info-box {
    background: #eff6ff;
    border: 1px solid #bfdbfe;
    border-radius: 10px;
    padding: 0.8rem 1rem;
    font-size: 0.875rem;
    color: #1e40af;
    margin-bottom: 1rem;
}

/* ── Counter resultados ── */
.results-count {
    text-align: right;
    font-size: 0.82rem;
    color: #64748b;
    margin-bottom: 0.75rem;
}

/* ── Sidebar labels ── */
.sidebar-label {
    font-size: 0.72rem;
    font-weight: 700;
    color: #334155;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 0.4rem;
    display: block;
}

/* ── GRID DE CARDS ── */
.cards-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.75rem;
    align-items: stretch;
    margin-bottom: 1rem;
}
.cards-grid-1col {
    display: grid;
    grid-template-columns: 1fr;
    gap: 0.65rem;
    margin-bottom: 1rem;
}

.card-producto {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 1rem 1.15rem;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    transition: box-shadow 0.18s, border-color 0.18s;
    min-height: 120px;
}
.card-producto:hover {
    box-shadow: 0 5px 16px rgba(0,0,0,0.07);
    border-color: #cbd5e1;
}
.card-top { flex: 1; }

.badge-top {
    display: inline-block;
    background: #15803d;
    color: #fff;
    font-size: 0.63rem;
    font-family: 'DM Mono', monospace;
    padding: 0.1rem 0.45rem;
    border-radius: 4px;
    margin-bottom: 0.45rem;
}
.precio-card {
    font-size: 1.2rem;
    font-weight: 700;
    color: #15803d;
    font-family: 'DM Mono', monospace;
    margin-bottom: 0.2rem;
}
.titulo-card {
    font-size: 0.9rem;
    font-weight: 600;
    color: #1a1a2e;
    line-height: 1.4;
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
    margin-bottom: 0.2rem;
}
.meta-card {
    font-size: 0.77rem;
    color: #64748b;
    margin-top: 3px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.badge-fuente {
    display: inline-block;
    background: #f1f5f9;
    color: #475569;
    border-radius: 20px;
    padding: 1px 7px;
    font-size: 0.67rem;
    font-weight: 600;
    margin-left: 5px;
    vertical-align: middle;
    border: 1px solid #e2e8f0;
}
.card-bottom {
    border-top: 1px solid #f1f5f9;
    margin-top: 0.65rem;
    padding-top: 0.55rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 0.35rem;
}
.tel-numero {
    font-family: 'DM Mono', monospace;
    font-size: 0.97rem;
    font-weight: 600;
    color: #1d4ed8;
}
.tel-sub { font-size: 0.7rem; color: #64748b; margin-top: 1px; }
.wa-link {
    color: #15803d; text-decoration: none;
    font-family: 'DM Mono', monospace; font-size: 0.78rem; font-weight: 600;
}
.wa-link:hover { text-decoration: underline; }
.ver-link {
    font-size: 0.76rem; color: #64748b; text-decoration: none;
    border: 1px solid #e2e8f0; border-radius: 5px; padding: 0.22rem 0.6rem;
    white-space: nowrap; background: #f8fafc; transition: background 0.15s;
}
.ver-link:hover { background: #e2e8f0; color: #1a1a2e; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────
# CATEGORÍAS
# ─────────────────────────────────────────

CATEGORIAS = {
    "pollo":                "🍗 Pollo y Aves",
    "cerdo":                "🐷 Cerdo",
    "res":                  "🥩 Carne de Res",
    "pescado_mariscos":     "🦞 Pescado y Mariscos",
    "embutidos_procesados": "🌭 Embutidos y Procesados",
    "lacteos_huevos":       "🧀 Lácteos y Huevos",
    "granos_cereales":      "🍚 Granos y Cereales",
    "aceites_condimentos":  "🫙 Aceites y Condimentos",
    "frutas_vegetales":     "🥦 Frutas y Vegetales",
    "combos_variados":      "📦 Combos y Surtidos",
    "otros":                "🍽️ Otros",
}
CATEGORIAS_LIMPIO = {k: v.split(" ", 1)[1] for k, v in CATEGORIAS.items()}


def fmt_precio(v):
    if pd.isna(v):
        return "—"
    return f"${v:,.0f}"


# ─────────────────────────────────────────
# DATOS
# ─────────────────────────────────────────

@st.cache_data(ttl=300)
def cargar_datos() -> pd.DataFrame:
    if not DB_PATH.exists():
        return pd.DataFrame()
    conn = sqlite3.connect(str(DB_PATH))
    df = pd.read_sql_query("SELECT * FROM anuncios", conn)
    conn.close()
    return df


# ─────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────

def sidebar(df: pd.DataFrame):
    with st.sidebar:
        st.markdown("""
        <div style="padding: 1.1rem 0 1rem;">
            <div style="font-size:1.45rem; font-weight:800; color:#1a1a2e; letter-spacing:-0.5px;">
                🇨🇺 CubaComida
            </div>
            <div style="font-size:0.76rem; color:#94a3b8; margin-top:2px;">
                Precios de alimentos · La Habana
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.divider()

        # Categoría
        st.markdown('<span class="sidebar-label">🍽️ Categoría</span>', unsafe_allow_html=True)
        cats_en_db = [c for c in CATEGORIAS if c in df["categoria"].dropna().unique()]
        cat_sel = st.selectbox(
            "cat", options=cats_en_db,
            format_func=lambda x: CATEGORIAS.get(x, x),
            label_visibility="collapsed",
        )

        st.markdown("<div style='margin-top:1.1rem;'></div>", unsafe_allow_html=True)

        # Fuente
        st.markdown('<span class="sidebar-label">📡 Fuente</span>', unsafe_allow_html=True)
        fuentes_raw = df["fuente"].dropna().unique().tolist()
        fuente_sel = st.selectbox(
            "fuente", ["Todas"] + fuentes_raw,
            label_visibility="collapsed"
        )

        st.markdown("<div style='margin-top:0.9rem;'></div>", unsafe_allow_html=True)

        solo_mayorista = st.checkbox("Solo mayorista")

        st.markdown("<div style='margin-top:1rem;'></div>", unsafe_allow_html=True)
        st.divider()

        # Stats rápidas
        df_cat = df[df["categoria"] == cat_sel].dropna(subset=["precio_usd"])
        nombre_cat = CATEGORIAS_LIMPIO.get(cat_sel, cat_sel)

        st.markdown(
            f"<div style='font-size:0.82rem; font-weight:700; color:#1a1a2e; margin-bottom:0.55rem;'>"
            f"Resumen · {nombre_cat}</div>",
            unsafe_allow_html=True
        )

        stats = [("Anuncios", str(len(df_cat)))]
        if not df_cat.empty:
            stats += [
                ("Más barato", fmt_precio(df_cat["precio_usd"].min())),
                ("Promedio",   fmt_precio(df_cat["precio_usd"].mean())),
                ("Más caro",   fmt_precio(df_cat["precio_usd"].max())),
            ]

        rows_html = "".join(
            f'<div style="display:flex; justify-content:space-between; font-size:0.84rem; '
            f'padding:0.22rem 0; border-bottom:1px solid #f1f5f9;">'
            f'<span style="color:#64748b;">{lbl}</span>'
            f'<span style="font-weight:700; font-family:DM Mono,monospace; color:#1a1a2e;">{val}</span>'
            f'</div>'
            for lbl, val in stats
        )
        st.markdown(
            f'<div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:10px; padding:0.6rem 0.9rem;">'
            f'{rows_html}</div>',
            unsafe_allow_html=True
        )

        st.markdown(
            "<div style='margin-top:1.4rem; font-size:0.68rem; color:#cbd5e1; text-align:center;'>"
            "Facebook · Supermarket23 · TiendaHabana</div>",
            unsafe_allow_html=True
        )

    return cat_sel, fuente_sel, solo_mayorista


def filtrar(df, cat, fuente, solo_mayorista):
    df_f = df[df["categoria"] == cat].copy()
    if fuente != "Todas":
        df_f = df_f[df_f["fuente"] == fuente]
    if solo_mayorista:
        df_f = df_f[df_f["mayorista"] == 1]
    return df_f


# ─────────────────────────────────────────
# TARJETA DE PRODUCTO
# ─────────────────────────────────────────

def render_card(row, es_top=False) -> str:
    titulo = str(row.get("titulo", "Sin título"))
    if len(titulo) > 100:
        titulo = titulo[:97] + "…"

    precio = fmt_precio(row.get("precio_usd"))
    fuente_n = str(row.get("fuente_nombre", "")).strip()
    telefono = str(row["telefono"]) if pd.notna(row.get("telefono")) else None
    whatsapp = str(row["whatsapp"]) if pd.notna(row.get("whatsapp")) else None
    url = str(row["url"]) if pd.notna(row.get("url")) else None

    meta_parts = []
    if pd.notna(row.get("vendedor")) and str(row.get("vendedor")) not in ("nan", ""):
        meta_parts.append(str(row["vendedor"])[:30])
    if fuente_n and fuente_n != "nan":
        meta_parts.append(fuente_n[:30])
    meta = " · ".join(meta_parts) if meta_parts else "Sin información"

    badge_top = '<div class="badge-top">🔥 Mejor precio</div>' if es_top else ""
    badge_fuente = f'<span class="badge-fuente">{fuente_n}</span>' if fuente_n and fuente_n != "nan" else ""

    wa_html = ""
    if whatsapp and whatsapp != "nan":
        num = whatsapp.replace("+", "").replace(" ", "")
        if not num.startswith("53"):
            num = "53" + num
        wa_html = f' &nbsp;·&nbsp; <a class="wa-link" href="https://wa.me/{num}" target="_blank">WhatsApp ↗</a>'

    ver_html = ""
    if url and url != "nan":
        ver_html = f'<a class="ver-link" href="{url}" target="_blank">Ver anuncio →</a>'

    bottom_html = ""
    if telefono and telefono != "nan":
        bottom_html = f"""
        <div class="card-bottom">
            <div>
                <div class="tel-numero">📞 {telefono}</div>
                <div class="tel-sub">Llamar o SMS{wa_html}</div>
            </div>
            {ver_html}
        </div>"""
    elif url and url != "nan":
        bottom_html = f"""
        <div class="card-bottom" style="justify-content:flex-end;">
            {ver_html}
        </div>"""

    return f"""
    <div class="card-producto">
        <div class="card-top">
            {badge_top}
            <div class="precio-card">{precio}</div>
            <div class="titulo-card">{titulo}{badge_fuente}</div>
            <div class="meta-card">{meta}</div>
        </div>
        {bottom_html}
    </div>"""


def render_cards_grid(rows_iter, cols=2) -> str:
    css_class = "cards-grid" if cols == 2 else "cards-grid-1col"
    cards_html = "\n".join(render_card(row, es_top=es_top) for es_top, row in rows_iter)
    return f'<div class="{css_class}">{cards_html}</div>'


# ─────────────────────────────────────────
# PÁGINAS
# ─────────────────────────────────────────

def pagina_inicio(df: pd.DataFrame, cat: str):
    nombre_cat = CATEGORIAS_LIMPIO.get(cat, cat)
    emoji = CATEGORIAS.get(cat, "🍽️ ").split(" ")[0]
    st.markdown(f'<div class="app-titulo">{emoji} {nombre_cat}</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="app-subtitulo">Precios actuales en La Habana · Facebook y tiendas online</div>',
        unsafe_allow_html=True
    )

    df_cat = df[df["categoria"] == cat].dropna(subset=["precio_usd"])
    if df_cat.empty:
        st.info("No hay anuncios con precio para esta categoría.")
        return

    c1, c2, c3, c4 = st.columns(4)
    metricas = [
        (c1, "",           str(len(df_cat)),                        "Anuncios"),
        (c2, "card-verde", fmt_precio(df_cat["precio_usd"].min()),  "Más barato"),
        (c3, "card-rojo",  fmt_precio(df_cat["precio_usd"].max()),  "Más caro"),
        (c4, "card-ambar", fmt_precio(df_cat["precio_usd"].mean()), "Promedio"),
    ]
    for col, cls, val, lbl in metricas:
        with col:
            st.markdown(
                f'<div class="card-metrica {cls}">'
                f'<div class="card-valor">{val}</div>'
                f'<div class="card-etiqueta">{lbl}</div>'
                f'</div>',
                unsafe_allow_html=True
            )

    st.markdown("<br>", unsafe_allow_html=True)

    col_iz, col_der = st.columns([1.4, 1])

    with col_iz:
        st.markdown('<div class="section-label">Distribución de precios</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-sub">Cada barra muestra cuántos anuncios tienen ese precio</div>', unsafe_allow_html=True)
        avg = df_cat["precio_usd"].mean()
        fig = px.histogram(
            df_cat, x="precio_usd", nbins=25,
            color_discrete_sequence=["#2563eb"],
            labels={"precio_usd": "Precio (USD)", "count": "Cantidad"},
        )
        fig.add_vline(x=avg, line_dash="dash", line_color="#b45309", line_width=2,
                      annotation_text=f"  Promedio: {fmt_precio(avg)}",
                      annotation_font_color="#b45309", annotation_font_size=12)
        fig.update_layout(
            paper_bgcolor="white", plot_bgcolor="white",
            font=dict(family="DM Sans", color="#1a1a2e", size=12),
            margin=dict(l=0, r=0, t=10, b=0), height=290, bargap=0.08,
            xaxis=dict(gridcolor="#f1f5f9", tickprefix="$", title="Precio (USD)"),
            yaxis=dict(gridcolor="#f1f5f9", title="Anuncios"),
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_der:
        st.markdown('<div class="section-label">Anuncios recientes</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-sub">Los últimos publicados</div>', unsafe_allow_html=True)
        recientes = df_cat.sort_values("fecha_scraping", ascending=False, na_position="last").head(8)
        for _, row in recientes.iterrows():
            precio = fmt_precio(row["precio_usd"])
            titulo = str(row["titulo"])[:55] + "…" if len(str(row["titulo"])) > 55 else str(row["titulo"])
            fuente_nombre = str(row.get("fuente_nombre", ""))[:35] or "—"
            st.markdown(f"""
            <div style='display:flex; justify-content:space-between; align-items:center;
                        padding:0.5rem 0; border-bottom:1px solid #f1f5f9;'>
                <div>
                    <div style='font-size:0.84rem; color:#1a1a2e; font-weight:500;'>{titulo}</div>
                    <div style='font-size:0.76rem; color:#64748b;'>{fuente_nombre}</div>
                </div>
                <div style='font-weight:700; color:#15803d; white-space:nowrap;
                            font-family:DM Mono,monospace; font-size:0.95rem; margin-left:1rem;'>
                    {precio}
                </div>
            </div>
            """, unsafe_allow_html=True)


def pagina_explorar(df: pd.DataFrame, cat: str):
    nombre_cat = CATEGORIAS_LIMPIO.get(cat, cat)
    st.markdown(f'<div class="app-titulo">Explorar {nombre_cat}</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="app-subtitulo">{len(df)} anuncios disponibles</div>',
        unsafe_allow_html=True
    )

    if df.empty:
        st.info("No hay anuncios con los filtros seleccionados.")
        return

    col_busq, col_orden = st.columns([3, 1])
    with col_busq:
        busqueda = st.text_input(
            "Buscar",
            placeholder="🔍  Buscar por nombre del producto...",
            label_visibility="collapsed"
        )
    with col_orden:
        orden = st.selectbox(
            "orden",
            ["Precio: menor a mayor", "Precio: mayor a menor", "Más recientes"],
            label_visibility="collapsed"
        )

    df_res = df.copy()
    if busqueda:
        df_res = df_res[df_res["titulo"].str.contains(busqueda, case=False, na=False)]

    if "menor" in orden:
        df_res = df_res.sort_values("precio_usd", ascending=True, na_position="last")
    elif "mayor" in orden:
        df_res = df_res.sort_values("precio_usd", ascending=False, na_position="last")
    else:
        df_res = df_res.sort_values("fecha_scraping", ascending=False, na_position="last")

    if busqueda and df_res.empty:
        st.info(f'No se encontraron resultados para "{busqueda}".')
        return

    st.markdown(
        f'<div class="results-count">{len(df_res)} resultado{"s" if len(df_res) != 1 else ""}</div>',
        unsafe_allow_html=True
    )

    top3_idx = set(df_res.head(3).index) if not df_res.empty else set()
    items = list(df_res.head(60).iterrows())
    rows_iter = ((idx in top3_idx, row) for idx, row in items)
    st.html(render_cards_grid(rows_iter, cols=2))

    if len(df_res) > 60:
        st.info(f"Mostrando 60 de {len(df_res)} anuncios. Usa el buscador para afinar.")

    csv_data = df_res.to_csv(index=False, encoding="utf-8-sig")
    st.download_button(
        "⬇️ Descargar lista en CSV",
        data=csv_data,
        file_name=f"cubacomida_{cat}.csv",
        mime="text/csv",
    )


def pagina_comparar(df: pd.DataFrame, cat: str):
    nombre_cat = CATEGORIAS_LIMPIO.get(cat, cat)
    st.markdown(f'<div class="app-titulo">Comparar precios — {nombre_cat}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="app-subtitulo">Así están los precios hoy</div>', unsafe_allow_html=True)

    df_p = df.dropna(subset=["precio_usd"])
    if df_p.empty:
        st.info("No hay anuncios con precio para comparar.")
        return

    pmin = df_p["precio_usd"].min()
    pmax = df_p["precio_usd"].max()
    pavg = df_p["precio_usd"].mean()
    pmed = df_p["precio_usd"].median()

    st.markdown(
        f'<div class="info-box">Hay <b>{len(df_p)}</b> anuncios con precio. '
        f'El más barato cuesta <b>{fmt_precio(pmin)}</b> y el más caro <b>{fmt_precio(pmax)}</b>. '
        f'La mitad de los anuncios están por debajo de <b>{fmt_precio(pmed)}</b>.</div>',
        unsafe_allow_html=True
    )

    c1, c2, c3, c4 = st.columns(4)
    metricas = [
        (c1, "card-verde", fmt_precio(pmin), "El más barato"),
        (c2, "card-rojo",  fmt_precio(pmax), "El más caro"),
        (c3, "card-ambar", fmt_precio(pavg), "Precio promedio"),
        (c4, "card-azul",  fmt_precio(pmed), "Precio mediano"),
    ]
    for col, cls, val, lbl in metricas:
        with col:
            st.markdown(
                f'<div class="card-metrica {cls}">'
                f'<div class="card-valor">{val}</div>'
                f'<div class="card-etiqueta">{lbl}</div>'
                f'</div>',
                unsafe_allow_html=True
            )

    st.markdown("<br>", unsafe_allow_html=True)

    col_iz, col_der = st.columns(2)

    with col_iz:
        st.markdown('<div class="section-label">¿Cómo están distribuidos los precios?</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-sub">Cada barra muestra cuántos anuncios tienen ese precio</div>', unsafe_allow_html=True)
        fig = px.histogram(
            df_p, x="precio_usd", nbins=20,
            color_discrete_sequence=["#2563eb"],
            labels={"precio_usd": "Precio (USD)", "count": "Anuncios"},
        )
        fig.add_vline(x=pavg, line_dash="dash", line_color="#b45309", line_width=2,
                      annotation_text=f"  Promedio {fmt_precio(pavg)}",
                      annotation_font_color="#b45309", annotation_font_size=11)
        fig.update_layout(
            paper_bgcolor="white", plot_bgcolor="white",
            font=dict(family="DM Sans", color="#1a1a2e", size=11),
            margin=dict(l=0, r=0, t=10, b=0), height=300, bargap=0.08,
            xaxis=dict(gridcolor="#f1f5f9", tickprefix="$", title="Precio (USD)"),
            yaxis=dict(gridcolor="#f1f5f9", title="Cantidad"),
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_der:
        st.markdown('<div class="section-label">¿Qué precio es normal y cuáles son extremos?</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-sub">La caja central muestra el rango de precios más comunes</div>', unsafe_allow_html=True)
        fig2 = go.Figure()
        fig2.add_trace(go.Box(
            y=df_p["precio_usd"],
            name=nombre_cat,
            marker_color="#2563eb",
            line_color="#2563eb",
            fillcolor="rgba(37,99,235,0.1)",
            boxpoints="outliers",
            hovertemplate="$%{y:.0f}<extra></extra>",
        ))
        fig2.update_layout(
            paper_bgcolor="white", plot_bgcolor="white",
            font=dict(family="DM Sans", color="#1a1a2e", size=11),
            margin=dict(l=0, r=0, t=10, b=0), height=300,
            showlegend=False,
            yaxis=dict(gridcolor="#f1f5f9", tickprefix="$", title="Precio (USD)"),
            xaxis=dict(showgrid=False),
        )
        st.plotly_chart(fig2, use_container_width=True)

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown('<div class="section-label">Los 5 más económicos ahora mismo</div>', unsafe_allow_html=True)
        baratos = df_p.nsmallest(5, "precio_usd")[["titulo", "precio_usd", "vendedor", "fuente_nombre"]].copy()
        baratos["precio_usd"] = baratos["precio_usd"].apply(fmt_precio)
        baratos.columns = ["Producto", "Precio", "Vendedor", "Fuente"]
        st.dataframe(baratos.fillna("—"), hide_index=True, use_container_width=True)

    with col_b:
        st.markdown('<div class="section-label">Los 5 más caros ahora mismo</div>', unsafe_allow_html=True)
        caros = df_p.nlargest(5, "precio_usd")[["titulo", "precio_usd", "vendedor", "fuente_nombre"]].copy()
        caros["precio_usd"] = caros["precio_usd"].apply(fmt_precio)
        caros.columns = ["Producto", "Precio", "Vendedor", "Fuente"]
        st.dataframe(caros.fillna("—"), hide_index=True, use_container_width=True)


def pagina_ranking(df: pd.DataFrame, cat: str):
    nombre_cat = CATEGORIAS_LIMPIO.get(cat, cat)
    st.markdown(f'<div class="app-titulo">Los más baratos — {nombre_cat}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="app-subtitulo">Ordenados de menor a mayor precio</div>', unsafe_allow_html=True)

    df_p = df.dropna(subset=["precio_usd"]).sort_values("precio_usd")
    if df_p.empty:
        st.info("No hay anuncios con precio.")
        return

    top20 = df_p.head(20).copy()
    top20["label"] = top20["titulo"].str[:45]

    fig = px.bar(
        top20, x="precio_usd", y="label", orientation="h",
        color="precio_usd",
        color_continuous_scale=[[0, "#15803d"], [0.5, "#b45309"], [1, "#dc2626"]],
        labels={"precio_usd": "Precio (USD)", "label": ""},
        custom_data=["vendedor", "fuente_nombre"],
    )
    fig.update_traces(
        hovertemplate="<b>$%{x:.0f}</b><br>%{customdata[0]}<br>%{customdata[1]}<extra></extra>"
    )
    fig.update_layout(
        paper_bgcolor="white", plot_bgcolor="white",
        font=dict(family="DM Sans", color="#1a1a2e", size=11),
        margin=dict(l=0, r=0, t=10, b=0), height=520,
        coloraxis_showscale=False,
        yaxis=dict(gridcolor="#f1f5f9", autorange="reversed"),
        xaxis=dict(gridcolor="#f1f5f9", tickprefix="$", title="Precio en dólares"),
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="section-label">Lista completa</div>', unsafe_allow_html=True)

    cols_lista = [c for c in ["titulo", "precio_usd", "moneda", "vendedor", "fuente_nombre", "url"] if c in df_p.columns]
    df_lista = df_p[cols_lista].copy()
    df_lista["precio_usd"] = df_lista["precio_usd"].apply(fmt_precio)
    df_lista = df_lista.fillna("—")
    df_lista.columns = ["Producto", "Precio", "Moneda", "Vendedor", "Fuente", "Ver anuncio"][:len(cols_lista)]

    col_cfg = {}
    if "Ver anuncio" in df_lista.columns:
        col_cfg["Ver anuncio"] = st.column_config.LinkColumn("Ver anuncio")

    st.dataframe(df_lista, use_container_width=True, height=420,
                 hide_index=True, column_config=col_cfg)


def pagina_contactos(df: pd.DataFrame, cat: str):
    nombre_cat = CATEGORIAS_LIMPIO.get(cat, cat)
    st.markdown(f'<div class="app-titulo">Contactar vendedores — {nombre_cat}</div>', unsafe_allow_html=True)

    tiene_tel = "telefono" in df.columns and df["telefono"].notna().any()

    if tiene_tel:
        df_tel = df[df["telefono"].notna()].sort_values("precio_usd", na_position="last")
    else:
        df_tel = df.dropna(subset=["precio_usd"]).sort_values("precio_usd")

    st.markdown(
        f'<div class="app-subtitulo">{len(df_tel)} vendedores disponibles</div>',
        unsafe_allow_html=True
    )

    if df_tel.empty:
        st.info("No hay vendedores para esta selección.")
        return

    busqueda = st.text_input(
        "Buscar",
        placeholder="🔍  Buscar producto por nombre o marca...",
        label_visibility="collapsed"
    )
    if busqueda:
        df_tel = df_tel[df_tel["titulo"].str.contains(busqueda, case=False, na=False)]
        if df_tel.empty:
            st.info(f'Sin resultados para "{busqueda}".')
            return

    rows_iter = ((False, row) for _, row in df_tel.head(40).iterrows())
    st.html(render_cards_grid(rows_iter, cols=1))

    if len(df_tel) > 40:
        st.info(f"Mostrando 40 de {len(df_tel)} contactos. Usa el buscador para filtrar.")


# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────

def main():
    df = cargar_datos()

    if df.empty:
        st.error("No se encontró la base de datos.")
        st.info("Ejecuta primero: python scrapers/limpiador.py")
        return

    cat_sel, fuente_sel, solo_mayorista = sidebar(df)
    df_filtrado = filtrar(df, cat_sel, fuente_sel, solo_mayorista)

    emoji = CATEGORIAS.get(cat_sel, "🍽️ ").split(" ")[0]
    nombre_cat = CATEGORIAS_LIMPIO.get(cat_sel, cat_sel)
    st.markdown(
        f"<div style='font-size:1.65rem; font-weight:800; color:#1a1a2e; letter-spacing:-0.5px; margin-bottom:0.1rem;'>"
        f"{emoji} {nombre_cat}</div>"
        f"<div style='font-size:0.8rem; color:#64748b; margin-bottom:1.2rem;'>"
        f"Precios actuales · La Habana · Facebook y tiendas online</div>",
        unsafe_allow_html=True
    )

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🏠  Inicio",
        "🔍  Explorar",
        "📊  Comparar precios",
        "💰  Los más baratos",
        "📞  Contactar vendedores",
    ])

    with tab1: pagina_inicio(df, cat_sel)
    with tab2: pagina_explorar(df_filtrado, cat_sel)
    with tab3: pagina_comparar(df_filtrado, cat_sel)
    with tab4: pagina_ranking(df_filtrado, cat_sel)
    with tab5: pagina_contactos(df_filtrado, cat_sel)


if __name__ == "__main__":
    main()