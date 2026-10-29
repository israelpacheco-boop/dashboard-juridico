"""Dashboard jurídico de notas personales con feeds RSS legales (BOE y GovInfo)."""

from __future__ import annotations

import html
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterable
from urllib.error import URLError
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

import streamlit as st

RUTA_DATOS = Path(__file__).with_name("notas.json")
FEEDS = {
    "España": {
        "nombre": "Boletín Oficial del Estado",
        "url": "https://www.boe.es/rss/boe.php",
        "bandera": "🇪🇸",
        "icono": "⚖️",
    },
    "Estados Unidos": {
        "nombre": "GovInfo · Public Laws",
        "url": "https://www.govinfo.gov/rss/plaw.xml",
        "bandera": "🇺🇸",
        "icono": "🏛️",
    },
}
TITULARES_MOSTRAR = 10
TIMEOUT_RED = 8


# ───────────────────────── CSS ─────────────────────────
CSS = """
<style>
    /* ---------- tipografía global ---------- */
    html, body, [class*="css"], .stApp, .stMarkdown, .stTextInput, .stTextArea {
        font-family: 'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif;
    }

    /* ---------- paleta ---------- */
    :root {
        --primario: #0B2545;
        --primario-claro: #13315C;
        --dorado: #C9A961;
        --dorado-suave: #E6D5A8;
        --fondo: #F7F5F0;
        --superficie: #FFFFFF;
        --texto: #1A1D23;
        --texto-suave: #6B7280;
        --borde: #E5E1D8;
        --exito: #2F855A;
        --error: #9B2C2C;
    }

    .stApp { background-color: var(--fondo); }

    /* ---------- cabecera ---------- */
    .hero {
        background: linear-gradient(135deg, #0B2545 0%, #13315C 60%, #1E4A7A 100%);
        padding: 2rem 2.2rem;
        border-radius: 14px;
        color: #FFFFFF;
        margin-bottom: 1.6rem;
        box-shadow: 0 10px 30px rgba(11, 37, 69, 0.15);
        border-left: 6px solid var(--dorado);
    }
    .hero h1 {
        margin: 0;
        font-size: 2rem;
        font-weight: 700;
        letter-spacing: -0.5px;
        color: #FFFFFF;
    }
    .hero p {
        margin: 0.4rem 0 0 0;
        color: #D9E2EC;
        font-size: 0.98rem;
    }
    .hero .divisor {
        display: inline-block;
        width: 42px;
        height: 2px;
        background: var(--dorado);
        margin: 0.9rem 0 0 0;
    }

    /* ---------- tarjetas de notas ---------- */
    .tarjeta {
        background: var(--superficie);
        border: 1px solid var(--borde);
        border-left: 4px solid var(--dorado);
        border-radius: 10px;
        padding: 1.1rem 1.3rem;
        margin-bottom: 0.9rem;
        box-shadow: 0 2px 6px rgba(11, 37, 69, 0.05);
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    .tarjeta:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 18px rgba(11, 37, 69, 0.10);
    }
    .tarjeta-titulo {
        font-size: 1.08rem;
        font-weight: 600;
        color: var(--primario);
        margin: 0 0 0.35rem 0;
    }
    .tarjeta-meta {
        display: flex;
        gap: 0.6rem;
        flex-wrap: wrap;
        align-items: center;
        font-size: 0.78rem;
        color: var(--texto-suave);
        margin-bottom: 0.65rem;
    }
    .chip {
        background: var(--dorado-suave);
        color: #4A3B10;
        padding: 2px 10px;
        border-radius: 999px;
        font-weight: 600;
        font-size: 0.72rem;
        letter-spacing: 0.3px;
        text-transform: uppercase;
    }
    .chip-id {
        background: #EEF2F7;
        color: var(--primario);
        font-family: ui-monospace, Menlo, Consolas, monospace;
        text-transform: none;
        letter-spacing: 0;
    }
    .tarjeta-cuerpo {
        color: var(--texto);
        line-height: 1.55;
        font-size: 0.95rem;
        white-space: pre-wrap;
    }

    /* ---------- tarjetas de titulares ---------- */
    .noticia {
        background: var(--superficie);
        border: 1px solid var(--borde);
        border-radius: 10px;
        padding: 0.95rem 1.15rem;
        margin-bottom: 0.65rem;
        display: flex;
        gap: 0.9rem;
        align-items: flex-start;
        transition: border-color 0.15s ease, transform 0.15s ease;
    }
    .noticia:hover {
        border-color: var(--dorado);
        transform: translateX(2px);
    }
    .noticia-num {
        background: var(--primario);
        color: var(--dorado);
        min-width: 32px;
        height: 32px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 700;
        font-size: 0.85rem;
        flex-shrink: 0;
    }
    .noticia a {
        color: var(--primario);
        text-decoration: none;
        font-weight: 500;
        line-height: 1.45;
    }
    .noticia a:hover { color: var(--dorado); text-decoration: underline; }
    .noticia-texto { color: var(--texto); line-height: 1.45; }

    .fuente-caption {
        display: inline-block;
        background: #EEF2F7;
        color: var(--primario);
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.78rem;
        margin-bottom: 0.9rem;
        font-family: ui-monospace, Menlo, Consolas, monospace;
    }

    /* ---------- barra lateral ---------- */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0B2545 0%, #13315C 100%);
    }
    section[data-testid="stSidebar"] * { color: #E8EEF4 !important; }
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 { color: var(--dorado) !important; }
    section[data-testid="stSidebar"] [data-testid="stMetricValue"] {
        color: var(--dorado) !important;
        font-weight: 700;
    }

    /* ---------- pestañas ---------- */
    .stTabs [data-baseweb="tab-list"] {
        gap: 6px;
        background: transparent;
        border-bottom: 2px solid var(--borde);
    }
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        border-radius: 8px 8px 0 0;
        padding: 10px 18px;
        color: var(--texto-suave);
        font-weight: 500;
    }
    .stTabs [aria-selected="true"] {
        background: var(--superficie) !important;
        color: var(--primario) !important;
        border-bottom: 3px solid var(--dorado) !important;
        font-weight: 600;
    }

    /* ---------- botones ---------- */
    .stButton > button {
        border-radius: 8px;
        border: 1px solid var(--borde);
        background: var(--superficie);
        color: var(--primario);
        font-weight: 500;
        transition: all 0.15s ease;
    }
    .stButton > button:hover {
        border-color: var(--dorado);
        color: var(--dorado);
        background: var(--superficie);
    }
    .stFormSubmitButton > button {
        background: var(--primario);
        color: #FFFFFF;
        border: none;
        padding: 0.55rem 1.4rem;
        font-weight: 600;
    }
    .stFormSubmitButton > button:hover {
        background: var(--primario-claro);
        color: var(--dorado);
    }

    /* ---------- entradas ---------- */
    .stTextInput input, .stTextArea textarea {
        border-radius: 8px !important;
        border: 1px solid var(--borde) !important;
        background: var(--superficie) !important;
    }
    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: var(--dorado) !important;
        box-shadow: 0 0 0 2px rgba(201, 169, 97, 0.2) !important;
    }

    /* ---------- títulos de sección ---------- */
    .seccion-titulo {
        display: flex;
        align-items: center;
        gap: 0.6rem;
        color: var(--primario);
        font-size: 1.35rem;
        font-weight: 700;
        margin: 0.3rem 0 1rem 0;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid var(--dorado-suave);
    }

    /* ---------- estado vacío ---------- */
    .vacio {
        background: var(--superficie);
        border: 1px dashed var(--borde);
        border-radius: 10px;
        padding: 2rem;
        text-align: center;
        color: var(--texto-suave);
    }
    .vacio .icono { font-size: 2.4rem; display: block; margin-bottom: 0.5rem; }

    /* ocultar la cabecera por defecto de streamlit */
    header[data-testid="stHeader"] { background: transparent; }
    #MainMenu, footer { visibility: hidden; }
</style>
"""


# ───────────────────────── modelo ─────────────────────────
@dataclass
class Nota:
    titulo: str
    contenido: str
    categoria: str
    fecha: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])


def cargar_notas() -> list[Nota]:
    if not RUTA_DATOS.exists():
        return []
    try:
        datos = json.loads(RUTA_DATOS.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        st.warning(f"{RUTA_DATOS.name} está corrupto; se ignora.")
        return []
    return [Nota(**item) for item in datos]


def guardar_notas(notas: Iterable[Nota]) -> None:
    serializado = [asdict(n) for n in notas]
    RUTA_DATOS.write_text(
        json.dumps(serializado, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# ───────────────────────── RSS ─────────────────────────
def obtener_titulares(url: str, n: int = TITULARES_MOSTRAR) -> list[tuple[str, str]]:
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 (notas-dashboard)"})
    with urlopen(req, timeout=TIMEOUT_RED) as resp:
        contenido = resp.read()
    raiz = ET.fromstring(contenido)
    items = raiz.findall(".//item")[:n]
    titulares: list[tuple[str, str]] = []
    for item in items:
        titulo = (item.findtext("title") or "").strip()
        enlace = (item.findtext("link") or "").strip()
        if titulo:
            titulares.append((titulo, enlace))
    return titulares


@st.cache_data(ttl=600, show_spinner=False)
def titulares_cacheados(url: str, n: int) -> list[tuple[str, str]]:
    return obtener_titulares(url, n)


# ───────────────────────── helpers UI ─────────────────────────
def _estado_notas() -> list[Nota]:
    if "notas" not in st.session_state:
        st.session_state.notas = cargar_notas()
    return st.session_state.notas


def _formatear_fecha(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso)
        return dt.strftime("%d %b %Y · %H:%M")
    except ValueError:
        return iso


def _titulo_seccion(icono: str, texto: str) -> None:
    st.markdown(
        f'<div class="seccion-titulo"><span>{icono}</span><span>{html.escape(texto)}</span></div>',
        unsafe_allow_html=True,
    )


def _tarjeta_nota(n: Nota) -> None:
    cuerpo_html = (
        f'<div class="tarjeta">'
        f'  <div class="tarjeta-titulo">📜 {html.escape(n.titulo)}</div>'
        f'  <div class="tarjeta-meta">'
        f'    <span class="chip">{html.escape(n.categoria)}</span>'
        f'    <span class="chip chip-id">ID {html.escape(n.id)}</span>'
        f'    <span>🗓️ {_formatear_fecha(n.fecha)}</span>'
        f'  </div>'
        f'  <div class="tarjeta-cuerpo">{html.escape(n.contenido)}</div>'
        f'</div>'
    )
    col_tarjeta, col_accion = st.columns([10, 1])
    with col_tarjeta:
        st.markdown(cuerpo_html, unsafe_allow_html=True)
    with col_accion:
        st.write("")
        if st.button("🗑️", key=f"borrar_{n.id}", help="Borrar nota"):
            notas = _estado_notas()
            notas[:] = [x for x in notas if x.id != n.id]
            guardar_notas(notas)
            st.rerun()


def _estado_vacio(icono: str, mensaje: str) -> None:
    st.markdown(
        f'<div class="vacio"><span class="icono">{icono}</span>{html.escape(mensaje)}</div>',
        unsafe_allow_html=True,
    )


# ───────────────────────── paneles ─────────────────────────
def panel_nueva_nota() -> None:
    _titulo_seccion("➕", "Añadir nueva nota")
    with st.form("form_nueva_nota", clear_on_submit=True):
        col1, col2 = st.columns([2, 1])
        with col1:
            titulo = st.text_input("📌 Título", placeholder="Resumen breve de la nota")
        with col2:
            categoria = st.text_input("🏷️ Categoría", placeholder="p. ej. legal, cliente, caso-123")
        contenido = st.text_area(
            "📝 Contenido",
            height=180,
            placeholder="Escribe aquí el contenido completo de la nota…",
        )
        enviado = st.form_submit_button("💾 Guardar nota", use_container_width=True)
        if enviado:
            if not titulo.strip() or not contenido.strip() or not categoria.strip():
                st.error("⚠️ Título, contenido y categoría son obligatorios.")
                return
            nota = Nota(
                titulo=titulo.strip(),
                contenido=contenido.strip(),
                categoria=categoria.strip().lower(),
            )
            notas = _estado_notas()
            notas.append(nota)
            guardar_notas(notas)
            st.success(f"✅ Nota guardada correctamente · ID `{nota.id}`")


def panel_listar_notas() -> None:
    _titulo_seccion("📋", "Expediente de notas")
    notas = _estado_notas()
    if not notas:
        _estado_vacio("📭", "Aún no hay notas registradas. Crea la primera en la pestaña ‘Añadir’.")
        return
    categorias = sorted({n.categoria for n in notas})
    col1, col2 = st.columns([3, 2])
    with col1:
        filtro = st.multiselect("🏷️ Filtrar por categoría", categorias, default=categorias)
    with col2:
        orden = st.radio(
            "🔽 Orden",
            ["Más recientes", "Más antiguas"],
            horizontal=True,
            label_visibility="visible",
        )
    seleccionadas = [n for n in notas if n.categoria in filtro]
    seleccionadas.sort(key=lambda x: x.fecha, reverse=(orden == "Más recientes"))
    st.caption(f"📊 Mostrando **{len(seleccionadas)}** de **{len(notas)}** notas totales.")
    st.divider()
    for n in seleccionadas:
        _tarjeta_nota(n)


def panel_buscar_notas() -> None:
    _titulo_seccion("🔍", "Motor de búsqueda")
    col1, col2 = st.columns(2)
    with col1:
        texto = st.text_input("🔎 Texto a buscar", placeholder="Palabras en título o contenido").strip().lower()
    with col2:
        categoria = st.text_input("🏷️ Categoría exacta", placeholder="Opcional").strip().lower()

    notas = _estado_notas()

    def coincide(n: Nota) -> bool:
        if texto and texto not in n.titulo.lower() and texto not in n.contenido.lower():
            return False
        if categoria and categoria != n.categoria:
            return False
        return True

    if not texto and not categoria:
        _estado_vacio("🔍", "Introduce un término o una categoría para iniciar la búsqueda.")
        return

    resultados = sorted(
        (n for n in notas if coincide(n)),
        key=lambda x: x.fecha,
        reverse=True,
    )
    if not resultados:
        _estado_vacio("🫙", "Ningún resultado coincide con los filtros aplicados.")
        return
    st.caption(f"📊 **{len(resultados)}** resultado(s) encontrados.")
    st.divider()
    for n in resultados:
        _tarjeta_nota(n)


def panel_titulares() -> None:
    _titulo_seccion("📰", "Boletín legal internacional")
    col_desc, col_btn = st.columns([5, 1])
    with col_desc:
        st.caption("Titulares oficiales organizados por jurisdicción. Caché de 10 minutos.")
    with col_btn:
        if st.button("🔄 Refrescar", use_container_width=True):
            titulares_cacheados.clear()
            st.rerun()

    etiquetas = [f"{m['bandera']} {pais}" for pais, m in FEEDS.items()]
    pestañas = st.tabs(etiquetas)
    for pestaña, (pais, meta) in zip(pestañas, FEEDS.items()):
        with pestaña:
            st.markdown(
                f'<div class="fuente-caption">{meta["icono"]} {html.escape(meta["nombre"])} · {html.escape(meta["url"])}</div>',
                unsafe_allow_html=True,
            )
            try:
                with st.spinner(f"Cargando titulares de {pais}…"):
                    titulares = titulares_cacheados(meta["url"], TITULARES_MOSTRAR)
            except (URLError, ET.ParseError, TimeoutError, ValueError) as e:
                st.error(f"❌ No se pudo leer el feed: {e}")
                continue
            if not titulares:
                _estado_vacio("📭", "Sin titulares disponibles en este momento.")
                continue
            for i, (titulo, enlace) in enumerate(titulares, 1):
                texto_safe = html.escape(titulo)
                if enlace:
                    enlace_safe = html.escape(enlace, quote=True)
                    cuerpo = f'<a href="{enlace_safe}" target="_blank">{texto_safe}</a>'
                else:
                    cuerpo = f'<span class="noticia-texto">{texto_safe}</span>'
                st.markdown(
                    f'<div class="noticia">'
                    f'  <div class="noticia-num">{i}</div>'
                    f'  <div>{cuerpo}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )


# ───────────────────────── app ─────────────────────────
def main() -> None:
    st.set_page_config(
        page_title="Dashboard Jurídico · Notas y BOE",
        page_icon="⚖️",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(CSS, unsafe_allow_html=True)

    st.markdown(
        '<div class="hero">'
        '  <h1>⚖️ Dashboard Jurídico</h1>'
        '  <p>Gestión profesional de notas · Boletín oficial España &amp; EE. UU.</p>'
        '  <span class="divisor"></span>'
        '</div>',
        unsafe_allow_html=True,
    )

    notas = _estado_notas()
    categorias = sorted({n.categoria for n in notas})

    with st.sidebar:
        st.markdown("### ⚖️ Panel")
        st.caption("Resumen del expediente")
        st.metric("📒 Notas guardadas", len(notas))
        st.metric("🏷️ Categorías", len(categorias))
        st.divider()
        if categorias:
            st.markdown("#### Categorías activas")
            chips = " ".join(
                f'<span class="chip" style="margin:2px 4px 2px 0; display:inline-block;">{html.escape(c)}</span>'
                for c in categorias
            )
            st.markdown(chips, unsafe_allow_html=True)
            st.divider()
        st.markdown("#### 📂 Almacenamiento")
        st.caption(f"`{RUTA_DATOS.name}`")
        st.markdown("#### 📡 Fuentes legales")
        for pais, meta in FEEDS.items():
            st.caption(f"{meta['bandera']} {pais} — {meta['nombre']}")

    tab_add, tab_list, tab_buscar, tab_feed = st.tabs(
        ["➕  Añadir", "📋  Listar", "🔍  Buscar", "📰  Titulares legales"]
    )
    with tab_add:
        panel_nueva_nota()
    with tab_list:
        panel_listar_notas()
    with tab_buscar:
        panel_buscar_notas()
    with tab_feed:
        panel_titulares()


if __name__ == "__main__":
    main()
