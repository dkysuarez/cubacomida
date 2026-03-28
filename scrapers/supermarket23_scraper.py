"""
CubaComida — Scraper de Supermarket23 v1
Extrae productos de alimentos con precios estructurados (USD)
Compatible con tu estructura actual + limpiador.py
"""

import json, re, time, random, sys
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright, Playwright
from loguru import logger

# ─────────────────────────────────────────────
# RUTAS (igual que tu facebook_scraper)
# ─────────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "data" / "raw" / "supermarket23"
LOGS_DIR = BASE_DIR / "logs"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# ─────────────────────────────────────────────
# LOGS
# ─────────────────────────────────────────────

logger.remove()
logger.add(sys.stderr, level="DEBUG", colorize=True,
           format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}")
logger.add(str(LOGS_DIR / "supermarket23_scraper.log"),
           rotation="10 MB", retention="7 days", level="DEBUG", encoding="utf-8")

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

CHROMIUM_EXE = r"D:\CubaComida\cubacomida\.browsers\chromium-1208\chrome-win64\chrome.exe"
MAX_SCROLLS = 15  # por categoría
SCROLL_DELAY_MIN = 2.0
SCROLL_DELAY_MAX = 4.0

# Categorías principales de alimentos (puedes agregar más)
CATEGORIAS = [
    {"id": "1072", "nombre": "Carnes", "url": "https://www.supermarket23.com/es/categoria/1072"},
    {"id": "1155", "nombre": "Cerdo", "url": "https://www.supermarket23.com/es/categoria/1155"},
    {"id": "1158", "nombre": "Embutidos y ahumados", "url": "https://www.supermarket23.com/es/categoria/1158"},
    {"id": "1159", "nombre": "Pescados y mariscos", "url": "https://www.supermarket23.com/es/categoria/1159"},
    {"id": "1077", "nombre": "Otros alimentos", "url": "https://www.supermarket23.com/es/categoria/1077"},
    {"id": "1164", "nombre": "Condimentos y saborizantes", "url": "https://www.supermarket23.com/es/categoria/1164"},
    {"id": "1162", "nombre": "Conservas", "url": "https://www.supermarket23.com/es/categoria/1162"},
    {"id": "1263", "nombre": "Bistecs y chuletas", "url": "https://www.supermarket23.com/es/categoria/1263"},
    {"id": "1271", "nombre": "Vegetales y viandas", "url": "https://www.supermarket23.com/es/categoria/1271"},
]


# ─────────────────────────────────────────────
# BROWSER (igual que el tuyo)
# ─────────────────────────────────────────────

def nuevo_browser(p: Playwright, headless: bool = False):
    browser = p.chromium.launch(
        executable_path=CHROMIUM_EXE,
        headless=headless,
        args=["--no-sandbox", "--disable-blink-features=AutomationControlled",
              "--disable-dev-shm-usage", "--disable-notifications",
              "--disable-popup-blocking", "--window-size=1366,900"]
    )
    ctx = browser.new_context(
        viewport={"width": 1366, "height": 900},
        user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"),
        locale="es-ES", ignore_https_errors=True,
    )
    ctx.add_init_script("""
        Object.defineProperty(navigator,'webdriver',{get:()=>undefined});
        window.chrome={runtime:{}};
    """)
    return browser, ctx


# ─────────────────────────────────────────────
# JS EXTRACTOR (adaptado para Supermarket23)
# ─────────────────────────────────────────────

JS_EXTRACT = r"""
() => {
    const productos = [];
    // Selectores probables (el sitio es JS-heavy)
    const cards = document.querySelectorAll('div[class*="product"], div[class*="card"], div[class*="item"], article, .product, [data-product]');

    cards.forEach(el => {
        try {
            // Nombre
            let nombre = '';
            const titleEl = el.querySelector('h1, h2, h3, h4, .title, .product-name, [class*="name"]');
            if (titleEl) nombre = titleEl.innerText.trim();

            // Precio (busca cualquier texto con $ o número + USD)
            let precio = null;
            const priceTexts = Array.from(el.querySelectorAll('span, div, p, strong, b'))
                .map(e => e.innerText.trim())
                .filter(t => /\$?\d+[.,]?\d*/.test(t));
            if (priceTexts.length) {
                const match = priceTexts[0].match(/\$?(\d+[.,]?\d*)/);
                if (match) precio = parseFloat(match[1].replace(',', '.'));
            }

            // URL del producto
            let url = '';
            const link = el.querySelector('a[href*="/producto"], a[href*="/product"], a[href*="categoria"]');
            if (link) url = link.href.startsWith('http') ? link.href : 'https://www.supermarket23.com' + link.getAttribute('href');

            // Imagen y descripción corta
            const img = el.querySelector('img') ? el.querySelector('img').src : '';
            const descEl = el.querySelector('p, .description, [class*="desc"]');
            const descripcion = descEl ? descEl.innerText.trim().substring(0, 300) : '';

            if (nombre && precio && precio > 0) {
                productos.push({
                    nombre: nombre,
                    precio: precio,
                    moneda: "USD",
                    url_producto: url,
                    imagen: img,
                    descripcion: descripcion,
                    categoria: "" // se llena después
                });
            }
        } catch(e) {}
    });

    return productos;
}
"""


# ─────────────────────────────────────────────
# GUARDAR
# ─────────────────────────────────────────────

def guardar_json(productos: list, categoria: dict):
    if not productos:
        return
    nombre_archivo = re.sub(r'[^a-z0-9]', '_', categoria["nombre"].lower())
    path = OUTPUT_DIR / f"supermarket23_{categoria['id']}_{nombre_archivo}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(productos, f, ensure_ascii=False, indent=2)
    logger.info(f"✅ Guardado: {path.name} ({len(productos)} productos)")


# ─────────────────────────────────────────────
# SCRAPE CATEGORÍA
# ─────────────────────────────────────────────

def scrape_categoria(categoria: dict, page) -> list:
    print(f"\n{'─' * 60}")
    print(f"  📦 Categoría: {categoria['nombre']}")
    print(f"  🔗 {categoria['url']}")
    print(f"{'─' * 60}")

    page.goto(categoria["url"], timeout=60000, wait_until="domcontentloaded")
    time.sleep(4)  # espera inicial de carga JS

    # Espera que carguen productos
    try:
        page.wait_for_selector('div[class*="product"], div[class*="card"], article', timeout=15000)
    except:
        logger.warning("No se detectaron productos rápidamente")

    todos = []
    vistos = set()

    for i in range(MAX_SCROLLS):
        # Extraer
        raw = page.evaluate(JS_EXTRACT)

        agregados = 0
        for p in raw:
            clave = p["url_producto"] or p["nombre"]
            if clave in vistos:
                continue
            vistos.add(clave)
            p["categoria"] = categoria["nombre"]
            p["fecha_scraping"] = datetime.now().isoformat()
            p["fuente"] = "supermarket23"
            todos.append(p)
            agregados += 1

        print(f"  Scroll {i + 1:>2}: {len(todos):>4} productos (+{agregados})")

        if agregados == 0 and i > 3:
            break

        # Scroll suave
        page.evaluate("window.scrollBy(0, window.innerHeight * 0.8)")
        time.sleep(random.uniform(SCROLL_DELAY_MIN, SCROLL_DELAY_MAX))

    if todos:
        guardar_json(todos, categoria)
        print(f"  ✅ {categoria['nombre']}: {len(todos)} productos guardados")
    else:
        print(f"  ⚠️  {categoria['nombre']}: 0 productos (revisa selectores si es necesario)")

    return todos


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    print("\n" + "=" * 60)
    print("  CUBACOMIDA — SCRAPER SUPERMARKET23 v1")
    print("=" * 60)
    print(f"  Categorías: {len(CATEGORIAS)}")
    print(f"  Datos:      {OUTPUT_DIR}")
    print("=" * 60)

    with sync_playwright() as p:
        browser, ctx = nuevo_browser(p, headless=False)
        page = ctx.new_page()

        total = 0
        for cat in CATEGORIAS:
            try:
                productos = scrape_categoria(cat, page)
                total += len(productos)
            except Exception as e:
                logger.error(f"Error en {cat['nombre']}: {e}")
                print(f"  ❌ Error: {e}")

            # Pausa entre categorías
            if cat != CATEGORIAS[-1]:
                pausa = random.uniform(8, 15)
                print(f"  ⏳ Pausa {pausa:.0f}s antes de siguiente categoría...")
                time.sleep(pausa)

        ctx.close()
        browser.close()

        print("\n" + "=" * 60)
        print("  RESUMEN FINAL SUPERMARKET23")
        print("=" * 60)
        print(f"  Total productos extraídos: {total}")
        print(f"  📁 Carpeta: {OUTPUT_DIR}")
        print("\n¡Listo! Ahora puedes correr limpiador.py para unir con la data de Facebook.")
        print("=" * 60)


if __name__ == "__main__":
    main()