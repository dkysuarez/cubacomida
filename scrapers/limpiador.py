"""
CubaComida — Limpiador v2 (Mejorado)
Procesa JSONs de Facebook, Supermarket23 y TiendaHabana
Filtra ruido y crea base de datos unificada
"""

import json
import re
from datetime import datetime
from pathlib import Path
import sqlite3

from loguru import logger

# ─────────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIRS = [
    BASE_DIR / "data" / "raw" / "facebook",
    BASE_DIR / "data" / "raw" / "supermarket23",
    BASE_DIR / "data" / "raw" / "tiendahabana",
]

DB_PATH = BASE_DIR / "data" / "cubacomida.db"

# Tasas de cambio (actualiza según mercado informal)
TASAS = {
    "USD": 1.0,
    "MLC": 1.0,
    "CUP": 1 / 340,   # Ajusta según tasa actual
}

# ─────────────────────────────────────────────
# CATEGORÍAS MEJORADAS
# ─────────────────────────────────────────────

CATEGORIAS = {
    "pollo": ["pollo", "pechuga", "muslo", "contramuslo", "ala", "carcasa", "gallina"],
    "carne": ["res", "bistec", "filete", "palomilla", "bola negra", "carne de res", "lomo"],
    "cerdo": ["cerdo", "puerco", "costilla", "pernil", "lomo de cerdo", "chicharrón"],
    "picadillo": ["picadillo", "perrito", "salchicha", "mortadela", "chorizo", "jamón"],
    "mariscos": ["pescado", "camarón", "langosta", "cangrejo", "pulpo", "atún", "sardina"],
    "lacteos": ["queso", "leche", "mantequilla", "yogur", "yogurt", "natilla", "crema de leche"],
    "huevos": ["huevo", "huevos"],
    "arroz": ["arroz"],
    "granos": ["frijol", "frijoles", "lenteja", "garbanzo", "chícharo"],
    "harina": ["harina", "espagueti", "macarrón", "pasta"],
    "aceite": ["aceite"],
    "vegetales": ["yuca", "boniato", "malanga", "plátano", "papa", "cebolla", "tomate", "vianda"],
    "conservas": ["conserva", "enlatado", "lata de", "sardina en lata", "atún en lata"],
    "combos": ["combo", "paquete", "canasta", "jaba", "surtido"],
    "mayorista": ["caja de", "bulto", "quintal", "saco", "por mayor", "mayorista"],
}

PRIORIDAD_CATEGORIAS = [
    "pollo", "picadillo", "carne", "cerdo", "mariscos", "lacteos", "huevos",
    "arroz", "granos", "harina", "aceite", "vegetales", "conservas", "combos", "mayorista"
]

# Palabras que indican que NO es alimento (ruido)
NO_COMIDA = [
    "herramienta", "panel solar", "ropa", "vestido", "zapato", "celular", "iphone",
    "computadora", "mueble", "lavadora", "nevera", "aire acondicionado", "electrodoméstico",
    "pintura", "cemento", "tornillo", "destornillador", "aseo", "limpieza", "detergente"
]

# ─────────────────────────────────────────────
# PATRONES REGEX
# ─────────────────────────────────────────────

PATRON_PRECIO = re.compile(r'(?i)(?:\$|\b)(\d+[.,]?\d*)')
PATRON_MONEDA = re.compile(r'(?i)\b(USD|MLC|CUP|MN|pesos?|dólares?|dolares?)\b')

# ─────────────────────────────────────────────
# FUNCIONES AUXILIARES
# ─────────────────────────────────────────────

def normalizar_texto(texto: str) -> str:
    return texto.lower().strip() if texto else ""

def es_alimento_relevante(texto: str) -> bool:
    """Filtra productos que claramente no son comida"""
    texto_lower = normalizar_texto(texto)
    return not any(palabra in texto_lower for palabra in NO_COMIDA)

def detectar_categoria(texto: str) -> str:
    texto_norm = normalizar_texto(texto)
    for cat in PRIORIDAD_CATEGORIAS:
        for kw in CATEGORIAS.get(cat, []):
            if kw in texto_norm:
                return cat
    return "otros"

def detectar_mayorista(texto: str) -> bool:
    texto_norm = normalizar_texto(texto)
    indicadores = ["caja de", "bulto", "quintal", "saco", "por mayor", "mayorista", "al mayor", "combo"]
    return any(ind in texto_norm for ind in indicadores)

def extraer_precio_y_moneda(texto: str) -> tuple[float | None, str]:
    """Extrae precio de texto libre (usado principalmente en Facebook)"""
    match = PATRON_PRECIO.search(texto)
    precio = float(match.group(1).replace(",", ".")) if match else None

    moneda = "USD"
    m_moneda = PATRON_MONEDA.search(texto)
    if m_moneda:
        raw = m_moneda.group(1).upper()
        if raw in ["CUP", "MN", "PESOS", "PESO"]:
            moneda = "CUP"
        elif raw in ["MLC"]:
            moneda = "MLC"

    return precio, moneda

def precio_a_usd(precio: float | None, moneda: str) -> float | None:
    if precio is None:
        return None
    tasa = TASAS.get(moneda, 1.0)
    return round(precio * tasa, 2)

# ─────────────────────────────────────────────
# LIMPIADOR PRINCIPAL (funciona con todas las fuentes)
# ─────────────────────────────────────────────

def limpiar_item(item: dict) -> dict | None:
    """Procesa un item de cualquier fuente y devuelve None si no es relevante"""

    fuente = item.get("fuente", "").lower()

    # Determinar descripción y precio según la fuente
    if "facebook" in fuente:
        desc = item.get("descripcion", "") or item.get("titulo", "")
        precio = None
        moneda = "CUP"
        url = item.get("url_post", "") or item.get("url", "")
        vendedor = item.get("vendedor", "") or item.get("nombre_vendedor", "")
    else:
        # Tiendas (Supermarket23 o TiendaHabana)
        desc = item.get("nombre", "") or item.get("descripcion", "")
        precio = item.get("precio")
        moneda = item.get("moneda", "USD")
        url = item.get("url_producto", "") or item.get("url", "")
        vendedor = "Tienda Online"

    if not desc or len(desc) < 8:
        return None

    # Filtro 1: No es alimento
    if not es_alimento_relevante(desc):
        logger.debug(f"Descartado (no comida): {desc[:60]}")
        return None

    # Filtro 2: Extraer precio
    if precio is None:  # Facebook o tiendas sin precio directo
        precio, moneda = extraer_precio_y_moneda(desc)

    if precio is None or precio <= 0:
        if not detectar_mayorista(desc):
            logger.debug(f"Descartado (sin precio): {desc[:60]}")
            return None

    # Categorizar
    categoria = detectar_categoria(desc)
    mayorista = detectar_mayorista(desc)

    precio_usd = precio_a_usd(precio, moneda)

    return {
        "titulo": desc[:250],
        "descripcion": desc,
        "precio": precio,
        "moneda": moneda,
        "precio_usd": precio_usd,
        "unidad": "",                    # puedes mejorar después
        "cantidad": None,
        "categoria": categoria,
        "mayorista": mayorista,
        "telefono": "",
        "whatsapp": "",
        "vendedor": vendedor,
        "fuente": fuente or item.get("fuente", "tienda"),
        "fuente_nombre": item.get("fuente_nombre", ""),
        "url": url,
        "provincia": item.get("provincia", "La Habana"),
        "fecha_post": item.get("fecha_post"),
        "fecha_scraping": item.get("fecha_scraping", datetime.now().isoformat()),
    }

# ─────────────────────────────────────────────
# PROCESAR ARCHIVOS
# ─────────────────────────────────────────────

def procesar_archivo(ruta: Path) -> list[dict]:
    try:
        with open(ruta, encoding="utf-8") as f:
            data = json.load(f)

        # Si es lista de productos (tiendas) o lista de posts (facebook)
        if isinstance(data, list):
            items = data
        else:
            items = [data]

        limpios = []
        for item in items:
            limpio = limpiar_item(item)
            if limpio:
                limpios.append(limpio)

        logger.success(f"✅ {len(limpios)}/{len(items)} ítems procesados de {ruta.name}")
        return limpios
    except Exception as e:
        logger.error(f"Error procesando {ruta.name}: {e}")
        return []

# ─────────────────────────────────────────────
# GUARDAR EN SQLITE
# ─────────────────────────────────────────────

def guardar_en_sqlite(posts: list[dict]):
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    cur.executescript("""
        CREATE TABLE IF NOT EXISTS anuncios (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo          TEXT,
            descripcion     TEXT,
            precio          REAL,
            moneda          TEXT,
            precio_usd      REAL,
            categoria       TEXT,
            mayorista       INTEGER,
            vendedor        TEXT,
            fuente          TEXT,
            fuente_nombre   TEXT,
            url             TEXT,
            provincia       TEXT,
            fecha_scraping  TEXT,
            UNIQUE(url, descripcion)
        );

        CREATE INDEX IF NOT EXISTS idx_categoria ON anuncios(categoria);
        CREATE INDEX IF NOT EXISTS idx_precio_usd ON anuncios(precio_usd);
        CREATE INDEX IF NOT EXISTS idx_fuente ON anuncios(fuente);
    """)

    insertados = 0
    for p in posts:
        try:
            cur.execute("""
                INSERT OR IGNORE INTO anuncios 
                (titulo, descripcion, precio, moneda, precio_usd, categoria, mayorista,
                 vendedor, fuente, fuente_nombre, url, provincia, fecha_scraping)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                p["titulo"], p["descripcion"], p["precio"], p["moneda"], p["precio_usd"],
                p["categoria"], int(p["mayorista"]), p["vendedor"], p["fuente"],
                p["fuente_nombre"], p["url"], p["provincia"], p["fecha_scraping"]
            ))
            if cur.rowcount > 0:
                insertados += 1
        except Exception as e:
            logger.warning(f"Error insertando: {e}")

    con.commit()
    con.close()
    logger.success(f"💾 Base de datos: {insertados} nuevos registros guardados")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

if __name__ == "__main__":
    logger.info("🚀 Iniciando limpiador v2 - Procesando todas las fuentes...")

    todos_limpios = []

    for raw_dir in RAW_DIRS:
        if not raw_dir.exists():
            logger.warning(f"Carpeta no encontrada: {raw_dir}")
            continue

        json_files = list(raw_dir.glob("*.json"))
        logger.info(f"Procesando carpeta {raw_dir.name} → {len(json_files)} archivos")

        for archivo in json_files:
            posts = procesar_archivo(archivo)
            todos_limpios.extend(posts)

    logger.info(f"\nTotal ítems limpios: {len(todos_limpios)}")

    if todos_limpios:
        guardar_en_sqlite(todos_limpios)
        print(f"\n✅ Proceso terminado. Base de datos creada en: {DB_PATH}")
    else:
        logger.error("No se procesaron datos. Revisa que tengas archivos JSON en las carpetas raw.")

    print("\nPuedes consultar la base de datos con herramientas como DB Browser for SQLite.")