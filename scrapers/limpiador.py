"""
CubaComida — Limpiador v8
Simple y directo: busca $ seguido de número en CUALQUIER lugar
"""

import json
import re
from datetime import datetime
from pathlib import Path
import sqlite3
from loguru import logger

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIRS = [
    BASE_DIR / "data" / "raw" / "facebook",
    BASE_DIR / "data" / "raw" / "supermarket23",
    BASE_DIR / "data" / "raw" / "tiendahabana",
]
DB_PATH = BASE_DIR / "data" / "cubacomida.db"

TASAS = {"USD": 1.0, "MLC": 1.0, "CUP": 1 / 340}

# ─────────────────────────────────────────────
# PALABRAS CLAVE
# ─────────────────────────────────────────────
ALIMENTOS_KW = [
    "pollo", "nuggets", "pechuga", "muslo", "contramuslo", "ala", "carcasa",
    "san jacobos", "flamenquines", "cubos", "croqueta", "empanada",
    "carne", "cerdo", "puerco", "costilla", "pernil", "picadillo",
    "arroz", "americo", "frijol", "lenteja", "garbanzo",
    "queso", "gouda", "cheddar", "leche", "huevo", "aceite", "harina", "pasta", "mdm", "tyson",
    "paquete", "caja", "lb", "kg", "libra", "kilo", "pollo", "cerdo", "res",
]

RECHAZAR_KW = [
    "bicimoto", "topmaq", "ecoflow", "inversor", "panel solar",
    "cama", "colchón", "mueble", "pasta dental", "jabón", "mensajería",
    "recarga", "nauta", "celular", "iphone", "samsung", "laptop", "tablet",
]


# ─────────────────────────────────────────────
# EXTRACCIÓN DE PRECIO - SIMPLE Y DIRECTA
# ─────────────────────────────────────────────

def extraer_precio_simple(texto: str) -> tuple[float | None, str]:
    """
    Extrae el PRIMER precio válido encontrado en el texto.
    Simple: busca $ seguido de número, o número seguido de cup/usd/mlc
    """

    # 1. Buscar $1500, $ 1500, $1,500
    patron_dolar = re.compile(r'\$\s*(\d{1,6}(?:[.,]\d{1,2})?)')
    m = patron_dolar.search(texto)
    if m:
        precio_str = m.group(1).replace(',', '.')
        try:
            precio = float(precio_str)
            # Rechazar si es teléfono (8+ dígitos empezando con 5)
            if len(str(int(precio))) >= 8 and str(int(precio)).startswith('5'):
                pass
            else:
                # Precio en USD
                if 0.10 <= precio <= 1000:
                    return precio, "USD"
        except:
            pass

    # 2. Buscar "1500 cup" o "1500 CUP" o "1500 pesos"
    patron_con_moneda = re.compile(
        r'\b(\d{1,6}(?:[.,]\d{1,2})?)\s*(cup|mlc|usd|mn|pesos?|d[oó]lares?)\b',
        re.I
    )
    m = patron_con_moneda.search(texto)
    if m:
        precio_str = m.group(1).replace(',', '.')
        moneda_raw = m.group(2).upper()
        try:
            precio = float(precio_str)
            # Rechazar teléfonos
            if len(str(int(precio))) >= 8 and str(int(precio)).startswith('5'):
                return None, "CUP"

            if moneda_raw in ("CUP", "MN", "PESOS", "PESO"):
                moneda = "CUP"
            elif moneda_raw in ("MLC",):
                moneda = "MLC"
            else:
                moneda = "USD"

            precio_usd = precio * TASAS.get(moneda, TASAS["CUP"])
            if 0.10 <= precio_usd <= 1000:
                return precio, moneda
        except:
            pass

    # 3. Buscar números grandes (100-50000) que podrían ser CUP
    patron_numero_grande = re.compile(r'\b(\d{3,5}(?:[.,]\d{1,2})?)\b')
    for m in patron_numero_grande.finditer(texto):
        precio_str = m.group(1).replace(',', '.')
        try:
            precio = float(precio_str)
            # Rechazar teléfonos
            if len(str(int(precio))) >= 8 and str(int(precio)).startswith('5'):
                continue
            # Números entre 100 y 50000 (posibles precios en CUP)
            if 100 <= precio <= 50000:
                # Verificar que esté cerca de una palabra de comida
                contexto = texto[max(0, m.start()-30):min(len(texto), m.end()+30)]
                if any(kw in contexto.lower() for kw in ALIMENTOS_KW):
                    return precio, "CUP"
        except:
            pass

    return None, "CUP"


def extraer_todos_los_precios(texto: str) -> list[dict]:
    """
    Extrae TODOS los precios del texto para mostrar múltiples productos
    """
    resultados = []
    lineas = texto.split('\n')

    for i, linea in enumerate(lineas):
        if not linea.strip():
            continue

        # Buscar precio en esta línea
        precio, moneda = extraer_precio_simple(linea)
        if precio:
            # Buscar el nombre del producto (lo que está antes del precio en la línea)
            producto = linea[:50]
            # Limpiar: quitar el precio y moneda
            producto = re.sub(r'\$\s*\d+[.,]?\d*', '', producto)
            producto = re.sub(r'\d+\s*(cup|mlc|usd|mn|pesos?)', '', producto, flags=re.I)
            producto = re.sub(r'\s+', ' ', producto).strip()

            if len(producto) > 3 and any(kw in producto.lower() for kw in ALIMENTOS_KW):
                precio_usd = precio * TASAS.get(moneda, TASAS["CUP"])
                if 0.10 <= precio_usd <= 1000:
                    resultados.append({
                        "producto": producto[:50],
                        "precio": precio,
                        "moneda": moneda,
                        "precio_usd": round(precio_usd, 2)
                    })

    return resultados


def extraer_contacto(texto: str) -> tuple[str, str]:
    """(telefono, whatsapp)"""
    telefono = ""
    whatsapp = ""

    # Teléfono cubano (8 dígitos empieza con 5)
    tel_pattern = re.compile(r'\b(5[0-9]{7})\b')
    m = tel_pattern.search(texto)
    if m:
        telefono = m.group(1)
        whatsapp = telefono  # Mismo número para WhatsApp

    # WhatsApp link
    wa_link = re.search(r'https?://(?:wa\.me|whatsapp\.com|chat\.whatsapp\.com)[/\s]*([\dA-Za-z]+)', texto, re.I)
    if wa_link:
        whatsapp = wa_link.group(1)

    return telefono, whatsapp


def es_anuncio_comida(texto: str) -> bool:
    texto_lower = texto.lower()

    # Rechazar productos NO comida (prioridad alta)
    for palabra in RECHAZAR_KW:
        if palabra in texto_lower:
            logger.debug(f"Rechazado por: {palabra}")
            return False

    # Debe tener al menos una palabra de comida
    tiene_comida = any(kw in texto_lower for kw in ALIMENTOS_KW)
    if not tiene_comida:
        logger.debug("No tiene palabras de comida")
        return False

    return True


def limpiar_item(item: dict) -> dict | None:
    fuente = str(item.get("fuente", "")).lower()
    es_fb = "facebook" in fuente

    # Texto completo
    if es_fb:
        desc = str(item.get("descripcion", "") or item.get("titulo", "") or "").strip()
    else:
        desc = str(item.get("nombre", "") or item.get("descripcion", "") or "").strip()

    if not desc or len(desc) < 10:
        return None

    # Validar que sea comida
    if not es_anuncio_comida(desc):
        return None

    # Extraer contacto
    telefono, whatsapp = extraer_contacto(desc)

    # Extraer precio
    precio, moneda = extraer_precio_simple(desc)

    # Extraer todos los productos con precio
    todos_productos = extraer_todos_los_precios(desc)

    # URL
    if es_fb:
        url = str(item.get("url", "") or item.get("url_post", "") or "").strip()
    else:
        url = str(item.get("url_producto", "") or item.get("url", "") or "").strip()
    if url in ("nan", "None"):
        url = ""

    # Vendedor
    if es_fb:
        vendedor = str(item.get("vendedor", "") or "").strip()
        if vendedor in ("nan", "None"):
            vendedor = ""
    else:
        vendedor = "Tienda Online"

    # Calcular precio USD
    precio_usd = None
    if precio is not None:
        precio_usd = round(precio * TASAS.get(moneda, TASAS["CUP"]), 2)
        if precio_usd < 0.10 or precio_usd > 1000:
            precio = None
            precio_usd = None

    # Categoría
    categoria = detectar_categoria(desc)

    # Mayorista
    mayorista = 1 if any(kw in desc.lower() for kw in ["caja", "bulto", "lb", "libra", "kg", "kilo", "paquete", "x", "unidades"]) else 0

    # Productos detectados
    productos_str = " | ".join([f"{p['producto']}: {p['precio']} {p['moneda']}" for p in todos_productos[:3]]) if todos_productos else ""

    return {
        "titulo": desc[:200],
        "descripcion": desc,
        "precio": precio,
        "moneda": moneda if precio else "CUP",
        "precio_usd": precio_usd,
        "categoria": categoria,
        "mayorista": mayorista,
        "telefono": telefono,
        "whatsapp": whatsapp,
        "vendedor": vendedor,
        "fuente": fuente or "tienda",
        "fuente_nombre": str(item.get("fuente_nombre", "") or "").strip(),
        "url": url,
        "provincia": str(item.get("provincia", "La Habana") or "La Habana").strip(),
        "productos": productos_str,
        "fecha_post": item.get("fecha_post"),
        "fecha_scraping": datetime.now().isoformat(),
    }


def detectar_categoria(texto: str) -> str:
    t = texto.lower()
    if any(kw in t for kw in ["pollo", "nuggets", "pechuga", "muslo", "mdm", "tyson", "pargo", "pescado"]):
        return "pollo_y_pescado"
    if any(kw in t for kw in ["cerdo", "puerco", "san jacobos", "flamenquines", "costilla"]):
        return "cerdo"
    if any(kw in t for kw in ["arroz", "americo", "frijol", "lenteja"]):
        return "granos"
    if any(kw in t for kw in ["queso", "gouda", "cheddar", "leche"]):
        return "lacteos"
    return "otros"


def procesar_archivo(ruta: Path) -> list[dict]:
    try:
        with open(ruta, encoding="utf-8") as f:
            data = json.load(f)
        items = data if isinstance(data, list) else [data]
        ok = []
        for item in items:
            r = limpiar_item(item)
            if r and (r["precio"] is not None or r["telefono"]):
                ok.append(r)
                if r["precio"]:
                    logger.debug(f"💰 {r['precio']} {r['moneda']} - {r['titulo'][:50]}")
        logger.success(f"✅ {ruta.name}: {len(ok)} ok / {len(items)-len(ok)} descartados")
        return ok
    except Exception as e:
        logger.error(f"Error en {ruta.name}: {e}")
        return []


def guardar_en_sqlite(posts: list[dict]):
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS anuncios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT,
            descripcion TEXT,
            precio REAL,
            moneda TEXT,
            precio_usd REAL,
            categoria TEXT,
            mayorista INTEGER,
            telefono TEXT,
            whatsapp TEXT,
            vendedor TEXT,
            fuente TEXT,
            fuente_nombre TEXT,
            url TEXT,
            provincia TEXT,
            productos TEXT,
            fecha_post TEXT,
            fecha_scraping TEXT
        )
    """)

    insertados = 0
    for p in posts:
        try:
            cur.execute("""
                INSERT OR IGNORE INTO anuncios
                (titulo, descripcion, precio, moneda, precio_usd, categoria, mayorista,
                 telefono, whatsapp, vendedor, fuente, fuente_nombre, url,
                 provincia, productos, fecha_post, fecha_scraping)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                p["titulo"], p["descripcion"], p["precio"], p["moneda"], p["precio_usd"],
                p["categoria"], p["mayorista"], p["telefono"], p["whatsapp"], p["vendedor"],
                p["fuente"], p["fuente_nombre"], p["url"], p["provincia"],
                p["productos"], p["fecha_post"], p["fecha_scraping"],
            ))
            if cur.rowcount > 0:
                insertados += 1
        except Exception as e:
            logger.warning(f"Error insert: {e}")

    con.commit()
    con.close()
    logger.success(f"💾 {insertados} registros nuevos → {DB_PATH}")


if __name__ == "__main__":
    logger.info("🚀 CubaComida Limpiador v8 - Simple y directo")

    # TEST con tus ejemplos
    ejemplos = [
        "Tengo paquetes de pollo los más baratos del mercado solo poro $1500 son de 3.50 a 4.00 lb llamar 55596365",
        "Nuggets de pollo 1kg 2800 cup",
        "San Jacobos de Cerdo 2800 cup",
        "Cubos de ajo Precio: 0.67 usd",
        "Arroz Américo 50lb PRECIO 13250",
        "Pollo de 33lb PRECIO 13800",
    ]

    print("\n=== TEST ===")
    for ejemplo in ejemplos:
        precio, moneda = extraer_precio_simple(ejemplo)
        if precio:
            precio_usd = precio * TASAS.get(moneda, TASAS["CUP"])
            print(f"✅ '{ejemplo[:50]}...' → {precio} {moneda} (${precio_usd:.2f})")
        else:
            print(f"❌ '{ejemplo[:50]}...' → SIN PRECIO")

    # Procesar archivos reales
    todos = []
    for d in RAW_DIRS:
        if not d.exists():
            logger.warning(f"No existe: {d}")
            continue
        archivos = list(d.glob("*.json"))
        logger.info(f"📂 {d.name} → {len(archivos)} archivos")
        for f in archivos:
            todos.extend(procesar_archivo(f))

    if todos:
        guardar_en_sqlite(todos)
        print(f"\n✅ {len(todos)} anuncios guardados en {DB_PATH}")
    else:
        print("❌ No se procesaron datos")