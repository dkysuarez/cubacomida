"""
CubaComida — Scraper TiendaHabana v2.2 (Fix de conexión fuerte)
"""

import json, re, time, random, sys
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright, Playwright
from loguru import logger

# Rutas
BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "data" / "raw" / "tiendahabana"
LOGS_DIR = BASE_DIR / "logs"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

logger.remove()
logger.add(sys.stderr, level="INFO", colorize=True,
           format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}")
logger.add(str(LOGS_DIR / "tiendahabana_scraper.log"),
           rotation="10 MB", retention="7 days", level="DEBUG", encoding="utf-8")

CHROMIUM_EXE = r"D:\CubaComida\cubacomida\.browsers\chromium-1208\chrome-win64\chrome.exe"
MAX_SCROLLS = 20
SCROLL_DELAY = (3.5, 7.0)

CATEGORIAS = [
    {"nombre": "Carnes", "url": "https://tiendahabana.com/categoria-producto/carnes/"},
    {"nombre": "Conservas Cárnicos", "url": "https://tiendahabana.com/categoria-producto/conservas/carnicos/"},
    {"nombre": "Arroz", "url": "https://tiendahabana.com/categoria-producto/pastas-y-granos/arroz/"},
    {"nombre": "Combos", "url": "https://tiendahabana.com/categoria-producto/combos/"},
    {"nombre": "Tienda General", "url": "https://tiendahabana.com/tienda/"},
]

JS_EXTRACT = """
() => {
    const productos = [];
    const cards = document.querySelectorAll('ul.products li.product, .product, article.product');

    cards.forEach(card => {
        try {
            const nameEl = card.querySelector('.woocommerce-loop-product__title, h2, .product-title');
            let nombre = nameEl ? nameEl.innerText.trim() : '';

            let precio = null;
            const priceEl = card.querySelector('.price .woocommerce-Price-amount, .price');
            if (priceEl) {
                const text = priceEl.innerText.replace(/[^0-9.,]/g, '');
                const match = text.match(/(\\d+[.,]?\\d*)/);
                if (match) precio = parseFloat(match[1].replace(',', '.'));
            }

            const link = card.querySelector('a');
            let url = link ? link.href : '';

            if (nombre && precio && precio > 1) {
                productos.push({
                    nombre: nombre,
                    precio: precio,
                    moneda: "USD",
                    url_producto: url,
                    descripcion: nombre,
                    categoria: "",
                    fecha_scraping: new Date().toISOString(),
                    fuente: "tiendahabana"
                });
            }
        } catch(e) {}
    });
    return productos;
}
"""

def guardar_json(productos, categoria):
    if not productos: return
    safe_name = re.sub(r'[^a-z0-9áéíóúñ\\s-]', '_', categoria["nombre"].lower()).replace(' ', '_')
    path = OUTPUT_DIR / f"tiendahabana_{safe_name}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(productos, f, ensure_ascii=False, indent=2)
    logger.info(f"Guardado: {path.name} ({len(productos)} productos)")

def scrape_categoria(categoria, page):
    print(f"\n{'─' * 75}")
    print(f"  📦 {categoria['nombre']}")
    print(f"  🔗 {categoria['url']}")
    print(f"{'─' * 75}")

    try:
        # Intentamos con diferentes estrategias de espera
        response = page.goto(categoria["url"], timeout=120000)
        if response:
            print(f"  Status: {response.status}")
        time.sleep(8)  # Espera larga para que cargue todo
    except Exception as e:
        print(f"  ❌ Error al cargar: {e}")
        return []

    todos = []
    vistos = set()

    for i in range(MAX_SCROLLS):
        raw = page.evaluate(JS_EXTRACT)
        agregados = 0
        for p in raw:
            clave = p.get("url_producto") or p["nombre"]
            if clave in vistos: continue
            vistos.add(clave)
            p["categoria"] = categoria["nombre"]
            todos.append(p)
            agregados += 1

        print(f"  Scroll {i+1:>2} → {len(todos):>4} productos (+{agregados})")

        if agregados == 0 and i >= 5:
            break

        page.evaluate("window.scrollBy(0, window.innerHeight * 0.85)")
        time.sleep(random.uniform(*SCROLL_DELAY))

    if todos:
        guardar_json(todos, categoria)
        print(f"  ✅ {len(todos)} productos guardados")
    else:
        print("  ⚠️  No se extrajeron productos en esta ejecución")

    return todos

def nuevo_browser(p: Playwright, headless=False):
    browser = p.chromium.launch(
        executable_path=CHROMIUM_EXE,
        headless=headless,
        args=[
            "--no-sandbox",
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--disable-http2",               # importante
            "--ignore-certificate-errors",
            "--disable-features=IsolateOrigins,site-per-process",
            "--no-zygote"
        ]
    )
    ctx = browser.new_context(
        viewport={"width": 1366, "height": 900},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        locale="es-ES",
        extra_http_headers={"Accept-Language": "es-ES,es;q=0.9"}
    )
    ctx.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")
    return browser, ctx

def main():
    print("\n" + "="*80)
    print("  CUBACOMIDA — SCRAPER TIENDAHABANA v2.2 (Fix conexión fuerte)")
    print("="*80)

    with sync_playwright() as p:
        browser, ctx = nuevo_browser(p, headless=False)
        page = ctx.new_page()

        total = 0
        for cat in CATEGORIAS:
            try:
                prods = scrape_categoria(cat, page)
                total += len(prods)
            except Exception as e:
                print(f"  ❌ Error grave en {cat['nombre']}: {e}")

            if cat != CATEGORIAS[-1]:
                time.sleep(random.uniform(15, 25))   # pausa más larga entre categorías

        ctx.close()
        browser.close()

        print("\n" + "="*80)
        print(f"  RESUMEN FINAL: {total} productos extraídos")
        print(f"  📁 {OUTPUT_DIR}")
        print("="*80)

if __name__ == "__main__":
    main()