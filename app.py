"""
CubaComida — App Streamlit
Misma estructura que CubaPrecios pero para alimentos en La Habana.
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
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap');

html, body, [class*="css"], .stApp {
    font-family: 'DM Sans', sans-serif;
    background-color: #f8f9fb;
    color: #1a1a2e;
}

[data-testid="stSidebar"] {
    background-color: #ffffff !important;
    border-right: 1px solid #e8eaf0 !important;
    min-width: 280px !important;
    width: 280px !important;
}
[data-testid="stSidebarCollapseButton"] { display: none !important; }

#MainMenu, footer, header { visibility: hidden; }
.stDeployButton { display: none; }

.stTabs [data-baseweb="tab-list"] {
    gap: 0;
    background: #ffffff;
    border-bottom: 1px solid #e8eaf0;
    padding: 0 1rem;
    margin-bottom: 1.5rem;
    border-radius: 0;
}
.stTabs [data-baseweb="tab"] {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.875rem;
    font-weight: 500;
    color: #8890a4;
    padding: 0.8rem 1.2rem;
    border-bottom: 2px solid transparent;
    margin-bottom: -1px;
    border-radius: 0;
    background: transparent;
}
.stTabs [aria-selected="true"] {
    color: #1a1a2e !important;
    border-bottom: 2px solid #1a1a2e !important;
    background: transparent !important;
    font-weight: 600;
}
.stTabs [data-baseweb="tab"]:hover { color: #1a1a2e; background: #f8f9fb !important; }
.stTabs [data-baseweb="tab-highlight"] { display: none; }
.stTabs [data-baseweb="tab-border"] { display: none; }

.block-container { padding-top: 0 !important; max-width: 1200px; }

.app-titulo {
    font-size: 1.8rem;
    font-weight: 700;
    color: #1a1a2e;
    letter-spacing: -0.5px;
}
.app-subtitulo {
    font-size: 0.85rem;
    color: #8890a4;
    margin-top: 2px;
    margin-bottom: 1.2rem;
}

.card-metrica {
    background: #ffffff;
    border: 1px solid #e8eaf0;
    border-radius: 12px;
    padding: 1.2rem 1.4rem;
    margin-bottom: 1rem;
}
.card-valor {
    font-size: 1.9rem;
    font-weight: 700;
    color: #1a1a2e;
    font-family: 'DM Mono', monospace;
    line-height: 1.1;
}
.card-etiqueta {
    font-size: 0.75rem;
    color: #8890a4;
    margin-top: 4px;
    text-transform: uppercase;
    letter-spacing: 0.8px;
}
.card-verde .card-valor { color: #16a34a; }
.card-azul  .card-valor { color: #2563eb; }
.card-rojo  .card-valor { color: #dc2626; }
.card-ambar .card-valor { color: #d97706; }

.seccion {
    font-size: 1rem;
    font-weight: 600;
    color: #1a1a2e;
    margin-bottom: 0.6rem;
    margin-top: 0.2rem;
}
.seccion-sub {
    font-size: 0.8rem;
    color: #8890a4;
    margin-bottom: 0.8rem;
    margin-top: -0.4rem;
}

.stDataFrame { border: 1px solid #e8eaf0 !important; border-radius: 10px !important; }
.stDataFrame th {
    background-color: #f8f9fb !important;
    color: #8890a4 !important;
    font-size: 0.75rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.5px !important;
}

.stButton > button {
    background-color: #1a1a2e;
    color: #ffffff;
    border: none;
    border-radius: 8px;
    font-weight: 500;
    font-size: 0.875rem;
    padding: 0.5rem 1.2rem;
    font-family: 'DM Sans', sans-serif;
}
.stButton > button:hover { background-color: #2d2d4e; }

.stTextInput > div > div > input {
    border-radius: 8px !important;
    border: 1px solid #e8eaf0 !important;
    background: #ffffff !important;
    font-family: 'DM Sans', sans-serif !important;
}
.stSelectbox > div > div {
    border-radius: 8px !important;
    border: 1px solid #e8eaf0 !important;
    background: #ffffff !important;
}

.card-contacto {
    background: #ffffff;
    border: 1px solid #e8eaf0;
    border-radius: 12px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.75rem;
    transition: box-shadow 0.2s;
}
.card-contacto:hover { box-shadow: 0 2px 12px rgba(0,0,0,0.06); }
.titulo-producto {
    font-size: 0.95rem;
    font-weight: 600;
    color: #1a1a2e;
    line-height: 1.4;
}
.precio-producto {
    font-size: 1.1rem;
    font-weight: 700;
    color: #16a34a;
    font-family: 'DM Mono', monospace;
}
.tel-producto {
    font-family: 'DM Mono', monospace;
    font-size: 0.95rem;
    font-weight: 500;
    color: #2563eb;
}
.meta-producto { font-size: 0.8rem; color: #8890a4; margin-top: 4px; }

.info-box {
    background: #eff6ff;
    border: 1px solid #bfdbfe;
    border-radius: 10px;
    padding: 0.8rem 1rem;
    font-size: 0.875rem;
    color: #1e40af;
    margin-bottom: 1rem;
}

hr { border: none; border-top: 1px solid #e8eaf0; margin: 1rem 0; }

.sidebar-stat {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.35rem 0;
    border-bottom: 1px solid #f0f2f7;
    font-size: 0.82rem;
}
.sidebar-stat-label { color: #8890a4; }
.sidebar-stat-value { font-weight: 600; color: #1a1a2e; font-family: 'DM Mono', monospace; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────
# CATEGORÍAS
# ─────────────────────────────────────────

CATEGORIAS = {
    "pollo":               "🍗 Pollo y Aves",
    "cerdo":               "🐷 Cerdo",
    "res":                 "🥩 Carne de Res",
    "pescado_mariscos":    "🦞 Pescado y Mariscos",
    "embutidos_procesados":"🌭 Embutidos y Procesados",
    "lacteos_huevos":      "🧀 Lácteos y Huevos",
    "granos_cereales":     "🍚 Granos y Cereales",
    "aceites_condimentos": "🫙 Aceites y Condimentos",
    "frutas_vegetales":    "🥦 Frutas y Vegetales",
    "combos_variados":     "📦 Combos y Surtidos",
    "otros":               "🍽️ Otros",
}

CATEGORIAS_LIMPIO = {k: v.split(" ", 1)[1] for k, v in CATEGORIAS.items()}


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
        <div style='padding: 1rem 0 1.2rem'>
            <div style='font-size:1.5rem; font-weight:700; color:#1a1a2e; letter-spacing:-0.5px;'>
                🇨🇺 CubaComida
            </div>
            <div style='font-size:0.78rem; color:#8890a4; margin-top:3px;'>
                Precios de alimentos · La Habana
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.divider()

        # Categoría
        st.markdown("<div style='font-size:0.75rem; font-weight:600; color:#8890a4; text-transform:uppercase; letter-spacing:0.8px; margin-bottom:0.4rem;'>Categoría</div>", unsafe_allow_html=True)
        cats_en_db = [c for c in CATEGORIAS if c in df["categoria"].dropna().unique()]
        cat_sel = st.selectbox(
            "cat", options=cats_en_db,
            format_func=lambda x: CATEGORIAS.get(x, x),
            label_visibility="collapsed",
        )

        st.markdown("<div style='margin-top:1rem;'></div>", unsafe_allow_html=True)

        # Fuente
        st.markdown("<div style='font-size:0.75rem; font-weight:600; color:#8890a4; text-transform:uppercase; letter-spacing:0.8px; margin-bottom:0.4rem;'>Fuente</div>", unsafe_allow_html=True)
        fuentes_raw = df["fuente"].dropna().unique().tolist()
        fuentes_opciones = ["Todas"] + fuentes_raw
        fuente_sel = st.selectbox("fuente", fuentes_opciones, label_visibility="collapsed")

        st.markdown("<div style='margin-top:0.75rem;'></div>", unsafe_allow_html=True)

        solo_mayorista = st.checkbox("Solo mayorista")

        st.divider()

        # Stats de la categoría seleccionada
        df_cat = df[df["categoria"] == cat_sel].dropna(subset=["precio_usd"])
        nombre_cat = CATEGORIAS_LIMPIO.get(cat_sel, cat_sel)

        st.markdown(f"<div style='font-size:0.82rem; font-weight:600; color:#1a1a2e; margin-bottom:0.5rem;'>{nombre_cat}</div>", unsafe_allow_html=True)

        stats_sidebar = [("Anuncios", str(len(df_cat)))]
        if not df_cat.empty:
            stats_sidebar += [
                ("Más barato", f"${df_cat['precio_usd'].min():.0f}"),
                ("Promedio",   f"${df_cat['precio_usd'].mean():.0f}"),
                ("Más caro",   f"${df_cat['precio_usd'].max():.0f}"),
            ]

        for label, val in stats_sidebar:
            st.markdown(f"""
            <div class="sidebar-stat">
                <span class="sidebar-stat-label">{label}</span>
                <span class="sidebar-stat-value">{val}</span>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<div style='margin-top:1.5rem; font-size:0.72rem; color:#c0c4d0; text-align:center;'>Facebook · Tiendas online · La Habana</div>", unsafe_allow_html=True)

    return cat_sel, fuente_sel, solo_mayorista


def filtrar(df, cat, fuente, solo_mayorista):
    df_f = df[df["categoria"] == cat].copy()
    if fuente != "Todas":
        df_f = df_f[df_f["fuente"] == fuente]
    if solo_mayorista:
        df_f = df_f[df_f["mayorista"] == 1]
    return df_f


# ─────────────────────────────────────────
# PÁGINA: INICIO
# ─────────────────────────────────────────

def pagina_inicio(df: pd.DataFrame, cat: str):
    nombre_cat = CATEGORIAS_LIMPIO.get(cat, cat)
    st.markdown(f'<div class="app-titulo">{nombre_cat}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="app-subtitulo">Precios actuales en La Habana · Facebook y tiendas online</div>', unsafe_allow_html=True)

    df_cat = df[df["categoria"] == cat].dropna(subset=["precio_usd"])
    if df_cat.empty:
        st.info("No hay anuncios con precio para esta categoría.")
        return

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""<div class="card-metrica">
            <div class="card-valor">{len(df_cat)}</div>
            <div class="card-etiqueta">Anuncios</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class="card-metrica card-verde">
            <div class="card-valor">${df_cat['precio_usd'].min():.0f}</div>
            <div class="card-etiqueta">Más barato</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div class="card-metrica card-rojo">
            <div class="card-valor">${df_cat['precio_usd'].max():.0f}</div>
            <div class="card-etiqueta">Más caro</div>
        </div>""", unsafe_allow_html=True)
    with c4:
        st.markdown(f"""<div class="card-metrica card-ambar">
            <div class="card-valor">${df_cat['precio_usd'].mean():.0f}</div>
            <div class="card-etiqueta">Promedio</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    col_iz, col_der = st.columns([1.4, 1])

    with col_iz:
        st.markdown('<div class="seccion">Distribución de precios</div>', unsafe_allow_html=True)
        st.markdown('<div class="seccion-sub">Cada barra muestra cuántos anuncios tienen ese precio</div>', unsafe_allow_html=True)
        fig = px.histogram(
            df_cat, x="precio_usd", nbins=25,
            color_discrete_sequence=["#2563eb"],
            labels={"precio_usd": "Precio (USD)", "count": "Cantidad"},
        )
        avg = df_cat["precio_usd"].mean()
        fig.add_vline(x=avg, line_dash="dash", line_color="#d97706", line_width=2,
                      annotation_text=f"  Promedio: ${avg:.0f}",
                      annotation_font_color="#d97706", annotation_font_size=12)
        fig.update_layout(
            paper_bgcolor="white", plot_bgcolor="white",
            font=dict(family="DM Sans", color="#1a1a2e", size=12),
            margin=dict(l=0, r=0, t=10, b=0), height=300, bargap=0.08,
            xaxis=dict(gridcolor="#f0f2f7", tickprefix="$", title="Precio (USD)"),
            yaxis=dict(gridcolor="#f0f2f7", title="Anuncios"),
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_der:
        st.markdown('<div class="seccion">Anuncios recientes</div>', unsafe_allow_html=True)
        st.markdown('<div class="seccion-sub">Los últimos publicados</div>', unsafe_allow_html=True)
        recientes = df_cat.sort_values("fecha_scraping", ascending=False, na_position="last").head(8)
        for _, row in recientes.iterrows():
            precio = f"${row['precio_usd']:.0f}" if pd.notna(row["precio_usd"]) else "—"
            titulo = str(row["titulo"])[:55] + "..." if len(str(row["titulo"])) > 55 else str(row["titulo"])
            fuente_nombre = str(row.get("fuente_nombre", ""))[:35] or "—"
            st.markdown(f"""
            <div style='display:flex; justify-content:space-between; align-items:center;
                        padding:0.5rem 0; border-bottom:1px solid #f0f2f7;'>
                <div>
                    <div style='font-size:0.85rem; color:#1a1a2e;'>{titulo}</div>
                    <div style='font-size:0.78rem; color:#8890a4;'>{fuente_nombre}</div>
                </div>
                <div style='font-weight:700; color:#16a34a; white-space:nowrap;
                            font-family: DM Mono, monospace; font-size:0.95rem; margin-left:1rem;'>
                    {precio}
                </div>
            </div>
            """, unsafe_allow_html=True)


# ─────────────────────────────────────────
# PÁGINA: EXPLORAR
# ─────────────────────────────────────────

def pagina_explorar(df: pd.DataFrame, cat: str):
    nombre_cat = CATEGORIAS_LIMPIO.get(cat, cat)
    st.markdown(f'<div class="app-titulo">Explorar {nombre_cat}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="app-subtitulo">{len(df)} anuncios disponibles</div>', unsafe_allow_html=True)

    if df.empty:
        st.info("No hay anuncios con los filtros seleccionados.")
        return

    col_busq, col_orden, col_count = st.columns([3, 2, 1])
    with col_busq:
        busqueda = st.text_input("Buscar", placeholder="Buscar por nombre del producto...", label_visibility="collapsed")
    with col_orden:
        orden = st.selectbox("orden", ["Precio: menor a mayor", "Precio: mayor a menor", "Más recientes"], label_visibility="collapsed")

    df_res = df.copy()
    if busqueda:
        df_res = df_res[df_res["titulo"].str.contains(busqueda, case=False, na=False)]

    if "menor" in orden:
        df_res = df_res.sort_values("precio_usd", ascending=True, na_position="last")
    elif "mayor" in orden:
        df_res = df_res.sort_values("precio_usd", ascending=False, na_position="last")
    else:
        df_res = df_res.sort_values("fecha_scraping", ascending=False, na_position="last")

    with col_count:
        st.markdown(f"<div style='padding:0.6rem 0; font-size:0.85rem; color:#8890a4; text-align:right;'>{len(df_res)} resultados</div>", unsafe_allow_html=True)

    if busqueda and df_res.empty:
        st.info(f'No se encontraron resultados para "{busqueda}".')
        return

    cols_mostrar = [c for c in ["titulo", "precio_usd", "moneda", "vendedor", "fuente_nombre", "url"] if c in df_res.columns]
    df_tabla = df_res[cols_mostrar].copy()
    df_tabla["precio_usd"] = df_tabla["precio_usd"].apply(lambda x: f"${x:.0f}" if pd.notna(x) else "Sin precio")
    df_tabla.columns = ["Producto", "Precio", "Moneda", "Vendedor", "Fuente", "Ver anuncio"][:len(cols_mostrar)]
    df_tabla = df_tabla.fillna("—")

    col_cfg = {}
    if "Ver anuncio" in df_tabla.columns:
        col_cfg["Ver anuncio"] = st.column_config.LinkColumn("Ver anuncio")

    st.dataframe(df_tabla, use_container_width=True, height=500,
                 hide_index=True, column_config=col_cfg)

    csv_data = df_res.to_csv(index=False, encoding="utf-8-sig")
    st.download_button(
        "⬇️ Descargar lista en CSV",
        data=csv_data,
        file_name=f"cubacomida_{cat}.csv",
        mime="text/csv",
    )


# ─────────────────────────────────────────
# PÁGINA: COMPARAR
# ─────────────────────────────────────────

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

    st.markdown(f"""
    <div class="info-box">
        Hay <b>{len(df_p)}</b> anuncios con precio.
        El más barato cuesta <b>${pmin:.0f}</b> y el más caro <b>${pmax:.0f}</b>.
        La mitad de los anuncios están por debajo de <b>${pmed:.0f}</b>.
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""<div class="card-metrica card-verde">
            <div class="card-valor">${pmin:.0f}</div>
            <div class="card-etiqueta">El más barato</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class="card-metrica card-rojo">
            <div class="card-valor">${pmax:.0f}</div>
            <div class="card-etiqueta">El más caro</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div class="card-metrica card-ambar">
            <div class="card-valor">${pavg:.0f}</div>
            <div class="card-etiqueta">Precio promedio</div>
        </div>""", unsafe_allow_html=True)
    with c4:
        st.markdown(f"""<div class="card-metrica card-azul">
            <div class="card-valor">${pmed:.0f}</div>
            <div class="card-etiqueta">Precio del medio</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    col_iz, col_der = st.columns(2)

    with col_iz:
        st.markdown('<div class="seccion">¿Cómo están distribuidos los precios?</div>', unsafe_allow_html=True)
        st.markdown('<div class="seccion-sub">Cada barra muestra cuántos anuncios tienen ese precio</div>', unsafe_allow_html=True)
        fig = px.histogram(
            df_p, x="precio_usd", nbins=20,
            color_discrete_sequence=["#2563eb"],
            labels={"precio_usd": "Precio (USD)", "count": "Anuncios"},
        )
        fig.add_vline(x=pavg, line_dash="dash", line_color="#d97706", line_width=2,
                      annotation_text=f"  Promedio ${pavg:.0f}",
                      annotation_font_color="#d97706", annotation_font_size=11)
        fig.update_layout(
            paper_bgcolor="white", plot_bgcolor="white",
            font=dict(family="DM Sans", color="#1a1a2e", size=11),
            margin=dict(l=0, r=0, t=10, b=0), height=300, bargap=0.08,
            xaxis=dict(gridcolor="#f0f2f7", tickprefix="$", title="Precio (USD)"),
            yaxis=dict(gridcolor="#f0f2f7", title="Cantidad"),
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_der:
        st.markdown('<div class="seccion">¿Qué precio es normal y cuáles son extremos?</div>', unsafe_allow_html=True)
        st.markdown('<div class="seccion-sub">La caja central muestra el rango de precios más comunes</div>', unsafe_allow_html=True)
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
            yaxis=dict(gridcolor="#f0f2f7", tickprefix="$", title="Precio (USD)"),
            xaxis=dict(showgrid=False),
        )
        st.plotly_chart(fig2, use_container_width=True)

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown('<div class="seccion">Los 5 más económicos ahora mismo</div>', unsafe_allow_html=True)
        baratos = df_p.nsmallest(5, "precio_usd")[["titulo", "precio_usd", "vendedor", "fuente_nombre"]].copy()
        baratos["precio_usd"] = baratos["precio_usd"].apply(lambda x: f"${x:.0f}")
        baratos.columns = ["Producto", "Precio", "Vendedor", "Fuente"]
        st.dataframe(baratos.fillna("—"), hide_index=True, use_container_width=True)

    with col_b:
        st.markdown('<div class="seccion">Los 5 más caros ahora mismo</div>', unsafe_allow_html=True)
        caros = df_p.nlargest(5, "precio_usd")[["titulo", "precio_usd", "vendedor", "fuente_nombre"]].copy()
        caros["precio_usd"] = caros["precio_usd"].apply(lambda x: f"${x:.0f}")
        caros.columns = ["Producto", "Precio", "Vendedor", "Fuente"]
        st.dataframe(caros.fillna("—"), hide_index=True, use_container_width=True)


# ─────────────────────────────────────────
# PÁGINA: LOS MÁS BARATOS
# ─────────────────────────────────────────

def pagina_ranking(df: pd.DataFrame, cat: str):
    nombre_cat = CATEGORIAS_LIMPIO.get(cat, cat)
    st.markdown(f'<div class="app-titulo">Los más baratos — {nombre_cat}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="app-subtitulo">Ordenados de menor a mayor precio</div>', unsafe_allow_html=True)

    df_p = df.dropna(subset=["precio_usd"]).sort_values("precio_usd")
    if df_p.empty:
        st.info("No hay anuncios con precio.")
        return

    top20 = df_p.head(20).copy()
    top20["label"] = top20["titulo"].str[:40]

    fig = px.bar(
        top20, x="precio_usd", y="label", orientation="h",
        color="precio_usd",
        color_continuous_scale=[[0, "#16a34a"], [0.5, "#d97706"], [1, "#dc2626"]],
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
        yaxis=dict(gridcolor="#f0f2f7", autorange="reversed"),
        xaxis=dict(gridcolor="#f0f2f7", tickprefix="$", title="Precio en dólares"),
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="seccion">Lista completa</div>', unsafe_allow_html=True)

    cols_lista = [c for c in ["titulo", "precio_usd", "moneda", "vendedor", "fuente_nombre", "url"] if c in df_p.columns]
    df_lista = df_p[cols_lista].copy()
    df_lista["precio_usd"] = df_lista["precio_usd"].apply(lambda x: f"${x:.0f}")
    nombres = ["Producto", "Precio", "Moneda", "Vendedor", "Fuente", "Ver anuncio"][:len(cols_lista)]
    df_lista.columns = nombres

    col_cfg = {}
    if "Ver anuncio" in df_lista.columns:
        col_cfg["Ver anuncio"] = st.column_config.LinkColumn("Ver anuncio")

    st.dataframe(df_lista.fillna("—"), use_container_width=True, height=420,
                 hide_index=True, column_config=col_cfg)


# ─────────────────────────────────────────
# PÁGINA: CONTACTAR VENDEDORES
# ─────────────────────────────────────────

def pagina_contactos(df: pd.DataFrame, cat: str):
    nombre_cat = CATEGORIAS_LIMPIO.get(cat, cat)
    st.markdown(f'<div class="app-titulo">Contactar vendedores — {nombre_cat}</div>', unsafe_allow_html=True)

    # Intentar columna telefono si existe
    tiene_tel = "telefono" in df.columns and df["telefono"].notna().any()

    if tiene_tel:
        df_tel = df[df["telefono"].notna()].sort_values("precio_usd", na_position="last")
    else:
        # Si no hay teléfonos (datos de tiendas), mostrar todos con URL
        df_tel = df.dropna(subset=["precio_usd"]).sort_values("precio_usd")

    st.markdown(f'<div class="app-subtitulo">{len(df_tel)} vendedores disponibles</div>', unsafe_allow_html=True)

    if df_tel.empty:
        st.info("No hay vendedores para esta selección.")
        return

    busqueda = st.text_input("Buscar", placeholder="Buscar producto...", label_visibility="collapsed")
    if busqueda:
        df_tel = df_tel[df_tel["titulo"].str.contains(busqueda, case=False, na=False)]
        if df_tel.empty:
            st.info(f'Sin resultados para "{busqueda}".')
            return
        st.markdown(f"**{len(df_tel)}** resultados")

    st.markdown("<br>", unsafe_allow_html=True)

    for _, row in df_tel.head(40).iterrows():
        titulo   = str(row["titulo"])[:80] + "..." if len(str(row["titulo"])) > 80 else str(row["titulo"])
        precio   = f"${row['precio_usd']:.0f} USD" if pd.notna(row.get("precio_usd")) else "Precio a consultar"
        tel      = str(row["telefono"]) if tiene_tel and pd.notna(row.get("telefono")) else None
        whatsapp = str(row["whatsapp"]) if "whatsapp" in row and pd.notna(row.get("whatsapp")) else None
        vendedor = str(row["vendedor"]) if pd.notna(row.get("vendedor")) else None
        fuente_n = str(row.get("fuente_nombre", ""))[:40] or None
        url      = str(row["url"]) if pd.notna(row.get("url")) else None

        col_info, col_tel, col_acc = st.columns([3, 1.2, 1])

        with col_info:
            meta = []
            if vendedor and vendedor != "nan": meta.append(f"Vendedor: {vendedor}")
            if fuente_n:                       meta.append(f"Fuente: {fuente_n}")
            meta_str = " · ".join(meta) if meta else "Sin información adicional"
            st.markdown(f"""
            <div class="card-contacto">
                <div class="titulo-producto">{titulo}</div>
                <div style='margin-top:6px;'>
                    <span class="precio-producto">{precio}</span>
                </div>
                <div class="meta-producto">{meta_str}</div>
            </div>
            """, unsafe_allow_html=True)

        with col_tel:
            if tel and tel != "nan":
                st.markdown(f"""
                <div style='padding:1.2rem 0; text-align:center;'>
                    <div class="tel-producto">{tel}</div>
                    <div style='font-size:0.75rem; color:#8890a4; margin-top:2px;'>Llamar o SMS</div>
                </div>
                """, unsafe_allow_html=True)

        with col_acc:
            st.markdown("<div style='padding:0.6rem 0;'>", unsafe_allow_html=True)
            if url and url != "nan":
                st.link_button("Ver anuncio", url, use_container_width=True)
            if whatsapp and whatsapp != "nan":
                num_wa = whatsapp.replace("+", "").replace(" ", "")
                if not num_wa.startswith("53"):
                    num_wa = "53" + num_wa
                st.link_button("WhatsApp", f"https://wa.me/{num_wa}", use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

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

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🏠  Inicio",
        "🔍  Explorar",
        "📊  Comparar precios",
        "💰  Los más baratos",
        "📞  Contactar vendedores",
    ])

    with tab1:
        pagina_inicio(df, cat_sel)
    with tab2:
        pagina_explorar(df_filtrado, cat_sel)
    with tab3:
        pagina_comparar(df_filtrado, cat_sel)
    with tab4:
        pagina_ranking(df_filtrado, cat_sel)
    with tab5:
        pagina_contactos(df_filtrado, cat_sel)


if __name__ == "__main__":
    main()