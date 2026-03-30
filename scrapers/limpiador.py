"""
CubaComida — Limpiador v10
- PRECIO OBLIGATORIO: sin precio válido → descartado, nunca llega a la app
- Nunca guarda precio 0, precio 1 CUP ni precios absurdos
- Mínimo real: 1500 CUP / 4 USD. Máximo: 800 USD
- No confunde teléfonos ni pesos/cantidades con precios
- 10 categorías de alimentos bien diferenciadas
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
# CATEGORÍAS — keywords por categoría (orden importa: más específico primero)
# ─────────────────────────────────────────────
CATEGORIAS_KW: dict[str, list[str]] = {
    "pollo": [
        "pollo", "pechuga", "muslo", "contramuslo", "ala de pollo", "carcasa",
        "nuggets", "mdm", "tyson", "pollo entero", "pollo congelado",
        "flamenquines", "san jacobos",
    ],
    "cerdo": [
        "cerdo", "puerco", "costilla", "pernil", "lomo de cerdo",
        "chuleta", "masas de cerdo", "pierna de cerdo", "chorizo",
    ],
    "res": [
        "res", "carne de res", "bistec", "picadillo", "albóndiga",
        "carne molida", "falda", "osobuco",
    ],
    "pescado_mariscos": [
        "pargo", "pescado", "tilapia", "salmón", "salmon", "atún", "atun",
        "camarón", "camaron", "langosta", "pulpo", "calamar", "mariscos",
    ],
    "embutidos_procesados": [
        "salchicha", "jamón", "jamon", "mortadela", "pepperoni",
        "croqueta", "empanada", "hamburguesa", "hot dog", "filete empanado",
    ],
    "lacteos_huevos": [
        "queso", "gouda", "cheddar", "mozarela", "mozzarella", "queso crema",
        "leche", "yogur", "mantequilla", "crema de leche", "huevo",
    ],
    "granos_cereales": [
        "arroz", "americo", "frijol", "lenteja", "garbanzo", "chícharo",
        "chicharo", "harina", "maíz", "maiz", "avena", "pasta", "espagueti",
        "fideos", "macarrón", "macarron",
    ],
    "aceites_condimentos": [
        "aceite", "aceite de girasol", "aceite de oliva", "vinagre",
        "mayonesa", "ketchup", "mostaza", "salsa", "cubos de caldo",
        "condimento", "especias", "sal ", "azúcar", "azucar",
    ],
    "frutas_vegetales": [
        "tomate", "cebolla", "ajo", "pimiento", "papa", "yuca", "malanga",
        "plátano", "platano", "mango", "naranja", "limón", "limon",
        "aguacate", "pepino", "zanahoria", "lechuga", "col ", "boniato",
    ],
    "combos_variados": [
        "combo", "paquete variado", "surtido", "canasta", "jaba",
        "paquete de alimentos", "productos variados",
    ],
}

# Lista plana para chequeo rápido "¿es alimento?"
ALIMENTOS_KW: list[str] = [kw for kws in CATEGORIAS_KW.values() for kw in kws] + [
    "carne", "libra", "lb",
]

RECHAZAR_KW = [
    # Vehículos y transporte
    "bicimoto", "triciclo", "bicicleta", "moto ", "renta de auto", "renta tu auto",
    "alquiler de auto", "renta de carro", "kilometraje", "combustible", "aeropuerto",
    # Electrónica y electrodomésticos
    "ecoflow", "inversor", "panel solar", "celular", "iphone", "samsung",
    "laptop", "tablet", "computadora", "televisor", "tv ", "nevera", "refrigerador",
    "freezer", "aire acondicionado", "lavadora", "ventilador", "abanico",
    "microondas", "cafetera", "licuadora", "plancha", "batería interna", "batería de litio",
    # Construcción y hogar
    "topmaq", "azulejo", "cemento", "pintura", "bomba de agua", "mueble",
    "cama", "colchón", "colchon", "losa de cerámica", "losas de cerámica",
    "porcelanato", "cerámica", "ceramica", "acero inoxidable", "plataforma de",
    # Higiene y limpieza
    "pasta dental", "jabón", "jabon", "detergente", "cloro", "suavizante",
    "perfume", "desodorante",
    # Ropa y calzado
    "ropa", "calzado", "zapato", "tenis",
    # Servicios
    "mensajería", "mensajeria", "recarga", "nauta",
    # Básculas y equipos de pesaje (tienen "kg" pero no son comida)
    "báscula", "bascula", "balanza", "pesa digital", "pesa de",
]

# Señales explícitas de que viene un precio
SEÑALES_PRECIO = [
    r"precio",
    r"vale",
    r"cuesta",
    r"vendo\s+(?:a|por|en)",
    r"venta\s+a",
    r"oferto\s+a",
    r"oferta\s+a",
    r"disponible\s+a",
    r"a\s+tan\s+solo",
    r"por\s+solo",
]

# Teléfono cubano: 8 dígitos empezando con 5
PATRON_TELEFONO = re.compile(r'\b5[0-9]{7}\b')

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _es_telefono(texto: str, pos: int, numero: float) -> bool:
    """True si el número en `pos` dentro de `texto` parece teléfono cubano."""
    # Rango numérico de teléfonos cubanos: 50000000–59999999
    if 50_000_000 <= numero <= 59_999_999:
        return True
    # También si aparece en un contexto "llama/llamar/tel/whatsapp/wa"
    contexto = texto[max(0, pos - 25):pos + 12].lower()
    if any(kw in contexto for kw in ["llam", "tel", "whatsapp", "wa.", "contact", "escrib"]):
        return True
    return False


def _es_cantidad_peso(texto: str, pos_fin: int) -> bool:
    """True si lo que sigue al número es una unidad de peso/cantidad, no moneda."""
    sufijo = texto[pos_fin:pos_fin + 8].strip().lower()
    # Si dice "lb", "kg", "g", "oz" justo después → es peso, no precio
    return bool(re.match(r'^(lb|kg|g\b|oz|unid|pzas?|und)\b', sufijo))


def _precio_usd_valido(precio_usd: float) -> bool:
    """Rango razonable para alimentos en Cuba: ~$4 USD (≈1360 CUP) a $800 USD."""
    return 4.0 <= precio_usd <= 800.0


# ─────────────────────────────────────────────
# EXTRACCIÓN DE PRECIO
# ─────────────────────────────────────────────

def extraer_precio_simple(texto: str) -> tuple[float | None, str]:
    """
    Extrae el precio más confiable del texto de Facebook.
    Jerarquía (de más a menos confiable):
      1. (*$NÚMERO*) o $NÚMERO  — dólar explícito, dentro o fuera de asteriscos
      2. *NÚMERO* al final de línea / segmento — precio en negrita estilo Messenger
      3. NÚMERO + moneda nombrada (cup / mlc / usd / pesos / dólares)
      4. señal de precio + NÚMERO  (precio 2800, vale 3500…)
      5. NÚMERO suelto al final de línea después de descripción de producto
    """

    # ── 1. $NÚMERO (con o sin asteriscos/paréntesis de formato) ───────────
    patron_dolar = re.compile(r'[\(*\s]*\$\s*(\d{1,6}(?:[.,]\d{1,2})?)[\)*\s]*')
    for m in patron_dolar.finditer(texto):
        precio_str = m.group(1).replace(',', '.')
        try:
            precio = float(precio_str)
        except ValueError:
            continue
        if _es_telefono(texto, m.start(), precio):
            continue
        if _es_cantidad_peso(texto, m.end()):
            continue
        if _precio_usd_valido(precio):
            return precio, "USD"

    # ── 2. *NÚMERO* — precio en negrita (estilo Messenger/WhatsApp) ────────
    # Solo si el número tiene 4+ dígitos (CUP) o 2-3 dígitos razonables (USD)
    patron_asterisco = re.compile(r'\*(\d{2,6}(?:[.,]\d{1,2})?)\*')
    for m in patron_asterisco.finditer(texto):
        precio_str = m.group(1).replace(',', '.')
        try:
            precio = float(precio_str)
        except ValueError:
            continue
        if _es_telefono(texto, m.start(), precio):
            continue
        if _es_cantidad_peso(texto, m.end()):
            continue
        # Determinar moneda por magnitud
        if precio >= 500:
            moneda, precio_usd = "CUP", precio * TASAS["CUP"]
        else:
            moneda, precio_usd = "USD", precio
        if _precio_usd_valido(precio_usd):
            return precio, moneda

    # ── 3. NÚMERO + moneda nombrada ────────────────────────────────────────
    patron_con_moneda = re.compile(
        r'\b(\d{1,6}(?:[.,]\d{1,2})?)\s*(cup|mlc|usd|mn\b|pesos?|d[oó]lares?)',
        re.I
    )
    for m in patron_con_moneda.finditer(texto):
        precio_str = m.group(1).replace(',', '.')
        moneda_raw = m.group(2).upper()
        try:
            precio = float(precio_str)
        except ValueError:
            continue
        if _es_telefono(texto, m.start(), precio):
            continue
        if moneda_raw in ("CUP", "MN", "PESOS", "PESO"):
            moneda = "CUP"
        elif moneda_raw == "MLC":
            moneda = "MLC"
        else:
            moneda = "USD"
        precio_usd = precio * TASAS.get(moneda, TASAS["CUP"])
        if _precio_usd_valido(precio_usd):
            return precio, moneda

    # ── 4. señal de precio + número ────────────────────────────────────────
    señal_re = re.compile(
        r'(?:' + '|'.join(SEÑALES_PRECIO) + r')\s*:?\s*(\d{2,6}(?:[.,]\d{1,2})?)',
        re.I
    )
    for m in señal_re.finditer(texto):
        precio_str = m.group(1).replace(',', '.')
        try:
            precio = float(precio_str)
        except ValueError:
            continue
        if _es_telefono(texto, m.start(1), precio):
            continue
        if _es_cantidad_peso(texto, m.end(1)):
            continue
        moneda = "CUP" if precio >= 500 else "USD"
        precio_usd = precio * TASAS.get(moneda, TASAS["CUP"])
        if _precio_usd_valido(precio_usd):
            return precio, moneda

    # ── 5. NÚMERO suelto al final de línea (ej: "Pechuga 1lb 1700") ────────
    # Solo cuando hay palabra de alimento en la misma línea y el número es >= 1000
    for linea in texto.split('\n'):
        linea = linea.strip()
        if not linea:
            continue
        if not any(kw in linea.lower() for kw in ALIMENTOS_KW):
            continue
        # Buscar número al final de la línea (puede tener puntuación después)
        m = re.search(r'\b(\d{4,5})\s*$', linea.rstrip('.,;: '))
        if not m:
            continue
        try:
            precio = float(m.group(1))
        except ValueError:
            continue
        if _es_telefono(linea, m.start(), precio):
            continue
        if _es_cantidad_peso(linea, m.end()):
            continue
        precio_usd = precio * TASAS["CUP"]
        if _precio_usd_valido(precio_usd):
            return precio, "CUP"

    return None, "CUP"


def extraer_todos_los_precios(texto: str) -> list[dict]:
    """
    Extrae todos los pares (producto, precio) de un texto con lista de productos.
    Solo cuenta líneas con señal de precio explícita.
    """
    resultados = []
    lineas = texto.split('\n')

    for linea in lineas:
        if not linea.strip():
            continue
        precio, moneda = extraer_precio_simple(linea)
        if precio is None:
            continue

        # Nombre: lo anterior al precio/símbolo en la línea
        producto = re.sub(r'\$\s*\d+[.,]?\d*', '', linea)
        producto = re.sub(r'\d+\s*(cup|mlc|usd|mn|pesos?)\b', '', producto, flags=re.I)
        producto = re.sub(r'(?:precio|vale|cuesta|vendo\s+a)[^a-zA-Z]*', '', producto, flags=re.I)
        producto = re.sub(r'\s+', ' ', producto).strip()

        if len(producto) > 3 and any(kw in producto.lower() for kw in ALIMENTOS_KW):
            precio_usd = precio * TASAS.get(moneda, TASAS["CUP"])
            if _precio_usd_valido(precio_usd):
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

    m = PATRON_TELEFONO.search(texto)
    if m:
        telefono = m.group(0)
        whatsapp = telefono

    wa_link = re.search(
        r'https?://(?:wa\.me|whatsapp\.com|chat\.whatsapp\.com)[/\s]*([\dA-Za-z]+)',
        texto, re.I
    )
    if wa_link:
        whatsapp = wa_link.group(1)

    return telefono, whatsapp


def es_anuncio_comida(texto: str) -> bool:
    texto_lower = texto.lower()
    for palabra in RECHAZAR_KW:
        if palabra in texto_lower:
            logger.debug(f"Rechazado por: {palabra}")
            return False
    if not any(kw in texto_lower for kw in ALIMENTOS_KW):
        logger.debug("No tiene palabras de comida")
        return False
    return True


def detectar_categoria(texto: str) -> str:
    """Clasifica en una de las 10 categorías usando CATEGORIAS_KW."""
    t = texto.lower()
    for categoria, keywords in CATEGORIAS_KW.items():
        if any(kw in t for kw in keywords):
            return categoria
    return "otros"


def limpiar_item(item: dict) -> dict | None:
    fuente = str(item.get("fuente", "")).lower()
    es_fb = "facebook" in fuente
    es_tienda = not es_fb  # supermarket23, tiendahabana, etc.

    # ── Texto del anuncio ──────────────────────────────────────────────────
    if es_fb:
        desc = str(item.get("descripcion", "") or item.get("titulo", "") or "").strip()
    else:
        # Para tiendas: nombre es el producto, descripcion suele ser solo la marca
        nombre = str(item.get("nombre", "") or "").strip()
        desc_raw = str(item.get("descripcion", "") or "").strip()
        # Usar nombre como texto principal; agregar descripcion solo si aporta
        desc = nombre if nombre else desc_raw
        if desc_raw and desc_raw.lower() not in desc.lower() and len(desc_raw) > 3:
            desc = f"{desc} {desc_raw}"

    if not desc or len(desc) < 5:
        return None

    if not es_anuncio_comida(desc):
        return None

    # ── Precio ────────────────────────────────────────────────────────────
    # Para tiendas: el precio ya viene limpio en el JSON — usarlo directamente
    if es_tienda and item.get("precio") is not None:
        try:
            precio = float(item["precio"])
            moneda_raw = str(item.get("moneda", "USD")).upper().strip()
            moneda = "CUP" if moneda_raw in ("CUP", "MN", "PESOS") else \
                     "MLC" if moneda_raw == "MLC" else "USD"
        except (ValueError, TypeError):
            precio, moneda = None, "USD"
    else:
        # Para Facebook: extraer del texto
        precio, moneda = extraer_precio_simple(desc)

    # Validar rango
    if precio is not None:
        precio_usd = round(precio * TASAS.get(moneda, TASAS["CUP"]), 2)
        if not _precio_usd_valido(precio_usd):
            precio, precio_usd = None, None
    else:
        precio_usd = None

    # SIN PRECIO VÁLIDO → descartado, nunca llega a la app
    if precio is None or precio_usd is None or precio_usd <= 0:
        return None

    # ── Contacto (solo relevante en Facebook) ─────────────────────────────
    telefono, whatsapp = extraer_contacto(desc)

    # ── URL ───────────────────────────────────────────────────────────────
    url = str(item.get("url_producto", "") or item.get("url_post", "") or item.get("url", "") or "").strip()
    if url in ("nan", "None", ""):
        url = ""

    # ── Vendedor ──────────────────────────────────────────────────────────
    if es_fb:
        vendedor = str(item.get("vendedor", "") or "").strip()
        if vendedor in ("nan", "None"):
            vendedor = ""
    else:
        vendedor = "Tienda Online"

    # ── Categoría ─────────────────────────────────────────────────────────
    # Para tiendas con categoría en el JSON, mapearla primero
    categoria_json = str(item.get("categoria", "") or "").lower()
    categoria = _mapear_categoria_json(categoria_json) or detectar_categoria(desc)

    # ── Mayorista ─────────────────────────────────────────────────────────
    mayorista = 1 if any(
        kw in desc.lower()
        for kw in ["caja", "bulto", "lb", "libra", "paquete", "unidades"]
    ) else 0

    # ── Productos múltiples (solo Facebook, anuncios con lista) ───────────
    todos_productos = extraer_todos_los_precios(desc) if es_fb else []
    productos_str = " | ".join(
        [f"{p['producto']}: {p['precio']} {p['moneda']}" for p in todos_productos[:3]]
    ) if todos_productos else ""

    return {
        "titulo": desc[:200],
        "descripcion": desc,
        "precio": precio,
        "moneda": moneda,
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


def _mapear_categoria_json(cat_json: str) -> str | None:
    """Mapea la categoría del JSON de tiendas a nuestras categorías internas.
    Devuelve None si no hay match claro — detectar_categoria usará el texto."""
    if not cat_json:
        return None
    c = cat_json.lower()
    if any(x in c for x in ["pollo", "ave", "pechuga", "nugget"]):
        return "pollo"
    if any(x in c for x in ["cerdo", "puerco"]):
        return "cerdo"
    if any(x in c for x in ["carne de res", "vacuno", "res "]):
        return "res"
    if any(x in c for x in ["pescado", "marisco", "camarón", "camaron", "tilapia", "pargo"]):
        return "pescado_mariscos"
    if any(x in c for x in ["embutido", "salchicha", "jamón", "jamon", "croqueta"]):
        return "embutidos_procesados"
    if any(x in c for x in ["lácteo", "lacteo", "queso", "leche", "huevo", "yogur"]):
        return "lacteos_huevos"
    if any(x in c for x in ["arroz", "grano", "frijol", "lenteja", "harina", "cereal", "pasta"]):
        return "granos_cereales"
    if any(x in c for x in ["aceite", "condimento", "sal", "azúcar", "azucar", "salsa"]):
        return "aceites_condimentos"
    if any(x in c for x in ["fruta", "vegetal", "vianda", "hortaliza", "verdura"]):
        return "frutas_vegetales"
    if any(x in c for x in ["combo", "surtido", "variado", "canasta"]):
        return "combos_variados"
    # "Carnes" genérico → NO asumir res, dejar que el texto del producto decida
    return None


def procesar_archivo(ruta: Path) -> list[dict]:
    try:
        with open(ruta, encoding="utf-8") as f:
            data = json.load(f)
        items = data if isinstance(data, list) else [data]
        ok = []
        for item in items:
            r = limpiar_item(item)
            if r:
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


# ─────────────────────────────────────────────
# TEST
# ─────────────────────────────────────────────

if __name__ == "__main__":
    logger.info("🚀 CubaComida Limpiador v10")

    # ── Test de categorías ────────────────────────────────────────────────
    print("\n=== CATEGORÍAS ===")
    casos_cat = [
        ("Pechuga de pollo congelada precio 4500 cup", "pollo"),
        ("Nuggets MDM tyson caja 10kg precio 8500 cup", "pollo"),
        ("Costilla de cerdo precio 5200 cup", "cerdo"),
        ("Pernil de puerco precio 6000 cup", "cerdo"),
        ("Picadillo de res 3800 cup", "res"),
        ("Bistec de res precio 4200 cup", "res"),
        ("Pargo fresco precio 2800 cup la libra", "pescado_mariscos"),
        ("Camarones precio $18 la libra", "pescado_mariscos"),
        ("Salchichas precio 1800 cup", "embutidos_procesados"),
        ("Jamón de pierna precio 3500 cup", "embutidos_procesados"),
        ("Queso gouda precio $12", "lacteos_huevos"),
        ("Huevos precio 2400 cup el cartón", "lacteos_huevos"),
        ("Arroz americo 50lb precio 13500 cup", "granos_cereales"),
        ("Frijoles negros precio 4500 cup", "granos_cereales"),
        ("Aceite de girasol precio $6", "aceites_condimentos"),
        ("Tomates precio 800 cup la libra", "frutas_vegetales"),
        ("Combo pollo cerdo arroz precio 15000 cup", "pollo"),  # primero que matchea
        ("Canasta surtida precio 20000 cup", "combos_variados"),
    ]
    ok_cat = 0
    for texto, cat_esp in casos_cat:
        cat_got = detectar_categoria(texto)
        ok = cat_got == cat_esp
        ok_cat += ok
        print(f"{'✅' if ok else '❌'} [{cat_got:<22}] esperaba [{cat_esp}]  →  {texto[:55]}")
    print(f"Categorías: {ok_cat}/{len(casos_cat)} correctas\n")

    # ── Test de precios ───────────────────────────────────────────────────
    print("=== PRECIOS ===")
    casos_precio = [
        # (texto, precio_esperado, descripcion)
        ("Pollo a $12 la libra llamar 55596365",            12.0,    "$ USD válido"),
        ("Nuggets de pollo 1kg 2800 cup",                   2800.0,  "número + cup"),
        ("San Jacobos precio 2800 cup",                     2800.0,  "señal precio + cup"),
        ("Arroz Américo 50lb PRECIO 13250",                 13250.0, "PRECIO + número grande"),
        ("Pollo de 33lb PRECIO 13800",                      13800.0, "PRECIO + número grande"),
        ("Caja de huevos $8",                               8.0,     "$ + 8 USD válido"),
        ("Queso gouda $45 el kg llama al 52341234",         45.0,    "$ válido, no confundir tel"),
        ("Pechuga 5200 cup whatsapp 53841234",              5200.0,  "cup + tel separado"),
        # Deben dar None (precio inválido o no existe)
        ("Pollo 3.50 lb disponible",                        None,    "peso, no precio"),
        ("Llama al 55678901 para info del pollo",           None,    "teléfono, no precio"),
        ("Cubos de ajo Precio: 0.67 usd",                  None,    "< 4 USD rechazado"),
        ("Carne de cerdo vendo a 350 pesos",               None,    "350 CUP = $1.03, rechazado"),
        ("Pollo entero a 1 cup",                           None,    "precio absurdo"),
        ("iPhone 14 $450",                                 None,    "rechazado: celular"),
        ("Panel solar 300w precio $180",                   None,    "rechazado: no comida"),
        ("$0 el pollo gratis",                             None,    "precio 0 rechazado"),
    ]
    ok_p = 0
    for texto, precio_esp, desc in casos_precio:
        es_comida = es_anuncio_comida(texto)
        if not es_comida:
            precio_got = None
        else:
            precio_got, moneda_got = extraer_precio_simple(texto)
            if precio_got is not None:
                pusd = precio_got * TASAS.get(moneda_got, TASAS["CUP"])
                if not _precio_usd_valido(pusd):
                    precio_got = None

        ok = (precio_got == precio_esp) or (precio_got is not None and precio_esp is not None and abs(precio_got - precio_esp) < 0.01)
        ok_p += ok
        got_str = f"{precio_got}" if precio_got is not None else "None"
        esp_str = f"{precio_esp}" if precio_esp is not None else "None"
        print(f"{'✅' if ok else '❌'} esp={esp_str:<10} got={got_str:<10}  {desc}  |  {texto[:50]}")

    print(f"\nPrecios: {ok_p}/{len(casos_precio)} correctos\n")

    # ── Procesar archivos reales ───────────────────────────────────────────
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
        # Resumen por categoría
        from collections import Counter
        cats = Counter(r["categoria"] for r in todos)
        print("\n📊 Distribución por categoría:")
        for cat, n in cats.most_common():
            print(f"   {cat:<25} {n:>4} anuncios")
        print(f"\n✅ {len(todos)} anuncios con precio válido guardados en {DB_PATH}")
    else:
        print("⚠️  No se procesaron archivos (directorios vacíos o inexistentes)")