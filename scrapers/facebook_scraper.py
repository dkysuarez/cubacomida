"""
CubaComida — Scraper de Facebook v8
Basado en diagnóstico real:
- feed > div tiene los posts (no role=article)
- data-ad-comet-preview="message" es el selector correcto para texto
- inner_text() falla en articles fuera del viewport — se usan hijos del feed
- Filtro de precio relajado: acepta número + contexto de precio (sin moneda = OK en Cuba)
- Espera robusta antes de extraer
- Scroll lento con pausa larga para activar lazy loading
"""

import json, re, time, random, sys
from datetime import datetime, timedelta
from pathlib import Path
from playwright.sync_api import sync_playwright, Playwright
from loguru import logger

# ─────────────────────────────────────────────
# RUTAS
# ─────────────────────────────────────────────

BASE_DIR      = Path(__file__).resolve().parent.parent
OUTPUT_DIR    = BASE_DIR / "data" / "raw" / "facebook"
LOGS_DIR      = BASE_DIR / "logs"
COOKIES_FILE  = BASE_DIR / "facebook_cookies.json"
PROGRESO_FILE = OUTPUT_DIR / "progreso_grupos.json"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# ─────────────────────────────────────────────
# LOGS
# ─────────────────────────────────────────────

logger.remove()
logger.add(sys.stderr, level="DEBUG", colorize=True,
           format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}")
logger.add(str(LOGS_DIR / "facebook_scraper.log"),
           rotation="10 MB", retention="7 days", level="DEBUG", encoding="utf-8")

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

CHROMIUM_EXE     = r"D:\CubaComida\cubacomida\.browsers\chromium-1208\chrome-win64\chrome.exe"
DIAS_ATRAS       = 30
MAX_SCROLLS      = 50
SCROLL_DELAY_MIN = 3.0
SCROLL_DELAY_MAX = 5.0

GRUPOS = [
    {"id": "1445123576384993",  "nombre": "Venta de comida en toda la Habana"},
    {"id": "819435256509392",   "nombre": "Compra y Venta de Comida en La Habana"},
    {"id": "9629254123815983",  "nombre": "Mipymes compra y venta de comida embutidos"},
    {"id": "1289139591990017",  "nombre": "Venta de cajas de pollo arroz y todo tipo"},
    {"id": "409161348160575",   "nombre": "Compra y Venta en La Habana arroz harina azucar"},
    {"id": "270688664506693",   "nombre": "Ventas de comida en La Habana"},
    {"id": "1053924772343244",  "nombre": "Pollo Picadillo y Carnicos LA HABANA"},
    {"id": "352966997521277",   "nombre": "Venta de alimentos la Habana"},
    {"id": "379360707124045",   "nombre": "Combos de alimentos en la Habana"},
    {"id": "3647504825578059",  "nombre": "Combos de comida habana"},
    {"id": "250290130002494",   "nombre": "Combos de comida habana 2"},
    {"id": "563128415344577",   "nombre": "Combos de comida Cuba"},
    {"id": "1064952304950249",  "nombre": "Compra y venta de alimentos en La Habana"},
    {"id": "375478485200043",   "nombre": "Venta de cajas de pollo Picadillo y perritos"},
    {"id": "666378742340624",   "nombre": "VENTAS MAYORISTAS CUBA"},
    {"id": "1887036955070095",  "nombre": "MIPYMES y TCP Comercio Mayorista"},
    {"id": "415824209939142",   "nombre": "Combos de alimentos"},
    {"id": "864427901153750",   "nombre": "Comida a domicilio en la Habana"},
    {"id": "284440339800615",   "nombre": "Ofertas de Combos en la Habana"},
    {"id": "3138973169653142",  "nombre": "Combos de comida para Cuba"},
]

# ─────────────────────────────────────────────
# PALABRAS CLAVE
# ─────────────────────────────────────────────

PALABRAS_ALIMENTOS = {
    'venta','vendo','oferta','combo','alimento','comida','hamburguesa',
    'pollo','arroz','frijol','frijoles','carne','picadillo','caja','paquete','pqt',
    'kg','libra','lb','mayorista','embutido','cerdo','res','ternera',
    'pescado','huevo','aceite','harina','azucar','azúcar',
    'leche','queso','yogur','jamón','jamon','chorizo','mortadella',
    'salchicha','camarones','mariscos','verdura','vegetal',
    'tomate','papa','boniato','malanga','platano','plátano',
    'naranja','mango','guayaba','aguacate','pepino','ajo','cebolla',
    'sazón','sazon','condimento','aceitunas','pasta','espagueti',
}

# ─────────────────────────────────────────────
# BROWSER
# ─────────────────────────────────────────────

def nuevo_browser(p: Playwright, headless: bool = False):
    browser = p.chromium.launch(
        executable_path=CHROMIUM_EXE,
        headless=headless,
        args=["--no-sandbox","--disable-blink-features=AutomationControlled",
              "--disable-dev-shm-usage","--disable-notifications",
              "--disable-popup-blocking","--window-size=1366,900"]
    )
    ctx = browser.new_context(
        viewport={"width":1366,"height":900},
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
# COOKIES / SESIÓN
# ─────────────────────────────────────────────

def guardar_cookies(ctx):
    with open(COOKIES_FILE,"w",encoding="utf-8") as f:
        json.dump(ctx.cookies(), f, ensure_ascii=False, indent=2)
    print("✅ Cookies guardadas")

def cargar_cookies(ctx) -> bool:
    if COOKIES_FILE.exists():
        with open(COOKIES_FILE) as f:
            ctx.add_cookies(json.load(f))
        return True
    return False

def sesion_existe() -> bool:
    return COOKIES_FILE.exists()

def borrar_sesion():
    if COOKIES_FILE.exists():
        COOKIES_FILE.unlink()
        print("🗑️  Sesión borrada")

def esta_logueado(page) -> bool:
    try:
        url = page.url.lower()
        if "login" in url or "checkpoint" in url:
            return False
        for sel in ['[data-pagelet="ProfileMenu"]','div[role="feed"]','a[href*="/groups/"]']:
            if page.query_selector(sel):
                return True
        return "facebook.com" in url
    except:
        return False

# ─────────────────────────────────────────────
# PROGRESO
# ─────────────────────────────────────────────

def cargar_progreso() -> dict:
    if PROGRESO_FILE.exists():
        with open(PROGRESO_FILE) as f: return json.load(f)
    return {}

def guardar_progreso(prog: dict):
    with open(PROGRESO_FILE,"w",encoding="utf-8") as f:
        json.dump(prog, f, ensure_ascii=False, indent=2)

# ─────────────────────────────────────────────
# LOGIN
# ─────────────────────────────────────────────

def hacer_login(p: Playwright) -> bool:
    print("\n" + "="*55)
    print("  INICIA SESIÓN EN FACEBOOK")
    print("="*55)
    browser, ctx = nuevo_browser(p, headless=False)
    page = ctx.new_page()
    try:
        page.goto("https://www.facebook.com", timeout=60000, wait_until="domcontentloaded")
        input("🔐 Completa el login y presiona ENTER...\n")
        time.sleep(3)
        guardar_cookies(ctx)
        print("✅ Login completado.")
    except Exception as e:
        print(f"❌ Error: {e}"); ctx.close(); browser.close(); return False
    ctx.close(); browser.close()
    return True

# ─────────────────────────────────────────────
# FECHAS
# ─────────────────────────────────────────────

def parsear_fecha(texto: str) -> str | None:
    if not texto: return None
    ahora = datetime.now()
    t = texto.lower().strip()
    meses = {"enero":1,"febrero":2,"marzo":3,"abril":4,"mayo":5,"junio":6,
              "julio":7,"agosto":8,"septiembre":9,"octubre":10,"noviembre":11,"diciembre":12}
    m = re.search(r"hace (\d+) min", t)
    if m: return (ahora - timedelta(minutes=int(m.group(1)))).isoformat()
    m = re.search(r"hace (\d+) hora", t)
    if m: return (ahora - timedelta(hours=int(m.group(1)))).isoformat()
    m = re.search(r"hace (\d+) d[íi]a", t)
    if m: return (ahora - timedelta(days=int(m.group(1)))).isoformat()
    if "ayer" in t: return (ahora - timedelta(days=1)).isoformat()
    if "hoy" in t: return ahora.isoformat()
    m = re.search(r"(\d{1,2})\s+de\s+(\w+)(?:\s+de\s+(\d{4}))?", t)
    if m:
        dia=int(m.group(1)); mes=meses.get(m.group(2))
        anio=int(m.group(3)) if m.group(3) else ahora.year
        if mes:
            try: return datetime(anio, mes, dia).isoformat()
            except: pass
    return None

def es_reciente(fecha_iso: str | None) -> bool:
    if not fecha_iso: return True
    try: return datetime.fromisoformat(fecha_iso) >= datetime.now() - timedelta(days=DIAS_ATRAS)
    except: return True

# ─────────────────────────────────────────────
# FILTRO PRECIO — AJUSTADO PARA CUBA
# En Cuba los precios suelen escribirse solo con número:
# "470 la caja", "a 470", "precio 470"
# También se acepta: usd, mlc, cup, $, mn, cuc
# Se descarta: posts sin ningún número que parezca precio
# ─────────────────────────────────────────────

def tiene_precio_valido(texto: str) -> bool:
    t = texto.lower()

    # Moneda explícita + número (cualquier orden)
    if re.search(r'\d+[\.,]?\d*\s*(usd|mlc|cup|mn|cuc)', t): return True
    if re.search(r'(usd|mlc|cup|mn|cuc)\s*\d+', t): return True
    if re.search(r'\$\s*\d+|\d+\s*\$', t): return True
    if re.search(r'gratis\b|precio\s+a\s+convenir', t): return True

    # Sin moneda explícita: acepta si hay número con contexto de precio
    # "a 470", "470 la", "precio 470", "por 470", "470 pesos", "470 cup"
    # O simplemente un número de 2-6 dígitos en contexto de venta
    patrones_precio_cuba = [
        r'\ba\s+\d{2,6}\b',           # "a 470"
        r'\bprecio\s+\d{2,6}\b',      # "precio 470"
        r'\bpor\s+\d{2,6}\b',         # "por 470"
        r'\d{2,6}\s+(la\s+)?(caja|pqt|paquete|libra|lb|kg|unidad|combo)',  # "470 la caja"
        r'\d{2,6}\s+pesos\b',         # "470 pesos"
        r'\bpv\b',                     # "más info al pv" (precio de venta)
        r'\bpm\b',                     # "precio al pm" (precio mayorista)
    ]
    for p in patrones_precio_cuba:
        if re.search(p, t): return True

    return False

# ─────────────────────────────────────────────
# VER MÁS
# ─────────────────────────────────────────────

def click_ver_mas(page) -> int:
    clickeados = 0
    for sel in [
        'div[role="button"]:has-text("Ver más")',
        'div[role="button"]:has-text("See more")',
        'span[role="button"]:has-text("Ver más")',
    ]:
        try:
            for btn in page.query_selector_all(sel):
                try:
                    btn.scroll_into_view_if_needed()
                    btn.click(timeout=2000)
                    clickeados += 1
                    time.sleep(0.3)
                except: pass
        except: pass
    if clickeados:
        logger.debug(f"Ver más: {clickeados} clicks")
    return clickeados

# ─────────────────────────────────────────────
# EXTRACTOR JAVASCRIPT
# Basado en el diagnóstico real:
# - feed > div son los posts
# - data-ad-comet-preview="message" tiene el texto
# - inner_text de article falla si está fuera del viewport
# ─────────────────────────────────────────────

JS_EXTRACT = r"""
() => {
    const resultados = [];
    const vistos = new Set();

    function limpiarURL(href) {
        if (!href) return '';
        if (href.startsWith('/')) href = 'https://www.facebook.com' + href;
        return href.split('?__cft__')[0].split('?__tn__')[0].split('&__cft__')[0];
    }

    function urlPost(el) {
        // Primero buscar permalink (grupos usan este)
        for (const sel of [
            'a[href*="/permalink/"]',
            'a[href*="/posts/"]',
            'a[href*="story_fbid"]',
        ]) {
            for (const a of el.querySelectorAll(sel)) {
                const h = a.getAttribute('href') || '';
                if (h.length > 20) return limpiarURL(h);
            }
        }
        // Fallback: link del grupo que tenga permalink o posts
        for (const a of el.querySelectorAll('a[href*="/groups/"]')) {
            const h = a.getAttribute('href') || '';
            if ((h.includes('/permalink') || h.includes('/posts')) && h.length > 30)
                return limpiarURL(h);
        }
        return '';
    }

    function perfilVendedor(el) {
        // Buscar por selectores específicos de perfil
        for (const sel of [
            'a[href*="/profile.php"]',
            'a[href*="/user/"]',
            'h2 a', 'h3 a', 'strong a',
        ]) {
            for (const a of el.querySelectorAll(sel)) {
                const h = a.getAttribute('href') || '';
                const t = (a.innerText || '').trim();
                if (h.length > 5 && t.length > 2 && t.length < 80)
                    return { nombre: t, url: limpiarURL(h) };
            }
        }
        // Fallback: primer link que parezca username de FB
        for (const a of el.querySelectorAll('a[href]')) {
            const h = a.getAttribute('href') || '';
            const t = (a.innerText || '').trim();
            if (h.startsWith('/') &&
                !h.startsWith('/groups') &&
                !h.startsWith('/hashtag') &&
                !h.startsWith('/pages') &&
                !h.includes('/posts') &&
                !h.includes('/permalink') &&
                h.split('/').length <= 3 &&
                t.length > 2 && t.length < 80)
                return { nombre: t, url: limpiarURL(h) };
        }
        return { nombre: '', url: '' };
    }

    function textoPost(el) {
        // 1. Selector exacto confirmado por debug
        const msg = el.querySelector(
            '[data-ad-comet-preview="message"], [data-ad-preview="message"]'
        );
        if (msg) {
            const t = (msg.innerText || '').trim();
            if (t.length > 10) return t;
        }
        // 2. div[dir="auto"] más largo (excluir los muy cortos)
        let mejor = '';
        for (const d of el.querySelectorAll('div[dir="auto"]')) {
            const t = (d.innerText || '').trim();
            if (t.length > mejor.length && t.length > 20) mejor = t;
        }
        if (mejor.length > 20) return mejor;
        // 3. Texto completo, saltando líneas de UI
        const ui = ['me gusta','comentar','compartir','ver más','see more',
                    'responder','reacciones','escribir un comentario'];
        const lineas = (el.innerText || '')
            .split('\n').map(l => l.trim()).filter(l => l.length > 10);
        for (let i = 1; i < lineas.length; i++) {
            const l = lineas[i].toLowerCase();
            if (!ui.some(w => l.includes(w)) && !l.match(/^\d+$/) && l.length > 15)
                return lineas[i];
        }
        return (el.innerText || '').trim().substring(0, 600);
    }

    function fechaPost(el) {
        // abbr con timestamp Unix (más preciso)
        for (const abbr of el.querySelectorAll('abbr[data-utime]')) {
            const ts = abbr.getAttribute('data-utime');
            if (ts) return new Date(parseInt(ts) * 1000).toISOString();
        }
        // abbr con title
        for (const abbr of el.querySelectorAll('abbr[title]')) {
            const t = abbr.getAttribute('title');
            if (t && t.length > 2) return t;
        }
        // span/a con texto relativo de tiempo
        for (const span of el.querySelectorAll('span, a')) {
            const t = (span.innerText || '').toLowerCase().trim();
            if (t.match(/hace \d+ (min|hora|d[íi]a)/) || t === 'ayer' || t === 'hoy')
                return t;
        }
        return '';
    }

    // ── Obtener los contenedores de posts ──────────────────
    // Basado en debug: feed > div tiene los posts reales
    let contenedores = [];

    const feed = document.querySelector('div[role="feed"]');
    if (feed && feed.children.length > 0) {
        contenedores = Array.from(feed.children);
        // Filtrar hijos vacíos o muy pequeños
        contenedores = contenedores.filter(el => (el.innerText || '').trim().length > 30);
    }

    // Fallback: role=article
    if (contenedores.length === 0) {
        contenedores = Array.from(document.querySelectorAll('div[role="article"]'))
            .filter(el => (el.innerText || '').trim().length > 30);
    }

    // Fallback: FeedUnit
    if (contenedores.length === 0) {
        contenedores = Array.from(document.querySelectorAll('div[data-pagelet^="FeedUnit"]'))
            .filter(el => (el.innerText || '').trim().length > 30);
    }

    // ── Procesar cada contenedor ───────────────────────────
    for (const el of contenedores) {
        try {
            const texto = textoPost(el);
            if (!texto || texto.length < 15) continue;

            const url_post = urlPost(el);
            // Deduplicar por url o por primeros 120 chars de texto
            const clave = url_post || texto.substring(0, 120);
            if (vistos.has(clave)) continue;
            vistos.add(clave);

            const v = perfilVendedor(el);

            resultados.push({
                descripcion:     texto,
                url_post:        url_post,
                nombre_vendedor: v.nombre,
                url_vendedor:    v.url,
                fecha_raw:       fechaPost(el),
            });
        } catch (e) {}
    }

    return resultados;
}
"""

# ─────────────────────────────────────────────
# FILTRAR Y ENRIQUECER
# ─────────────────────────────────────────────

def filtrar(raw: list, grupo: dict) -> list:
    resultado = []
    ahora = datetime.now().isoformat()
    for item in raw:
        desc = item.get("descripcion", "")
        tl = desc.lower()

        # Filtro 1: palabras de alimentos
        if not any(p in tl for p in PALABRAS_ALIMENTOS):
            logger.debug(f"⛔ Sin alimento: {desc[:70]}")
            continue

        # Filtro 2: precio (relajado para Cuba)
        if not tiene_precio_valido(desc):
            logger.debug(f"⛔ Sin precio: {desc[:70]}")
            continue

        # Parsear fecha
        fecha_iso = None
        fr = item.get("fecha_raw", "")
        if fr:
            if "T" in fr and len(fr) > 15:   # Ya es ISO del abbr data-utime
                fecha_iso = fr
            else:
                fecha_iso = parsear_fecha(fr)

        # Filtro 3: reciente
        if fecha_iso and not es_reciente(fecha_iso):
            logger.debug(f"⛔ Antiguo: {desc[:70]}")
            continue

        resultado.append({
            "titulo":        desc[:200],
            "descripcion":   desc,
            "vendedor":      item.get("nombre_vendedor", ""),
            "url_vendedor":  item.get("url_vendedor", ""),
            "url_post":      item.get("url_post", ""),
            "fecha_post":    fecha_iso,
            "fecha_raw":     fr,
            "fuente":        "facebook_grupo",
            "fuente_nombre": grupo["nombre"],
            "fuente_id":     grupo["id"],
            "provincia":     "La Habana",
            "fecha_scraping": ahora,
        })

    return resultado

# ─────────────────────────────────────────────
# EXTRACCIÓN
# ─────────────────────────────────────────────

def extraer(page, grupo: dict) -> list:
    try:
        raw = page.evaluate(JS_EXTRACT)
        logger.debug(f"JS extrajo {len(raw)} elementos")
        posts = filtrar(raw, grupo)
        logger.info(f"Filtrado: {len(raw)} → {len(posts)} válidos  |  grupo: {grupo['nombre']}")
        # Mostrar los primeros 2 para confirmar que funciona
        for p in posts[:2]:
            logger.debug(f"  ✅ {p['descripcion'][:80]}")
        return posts
    except Exception as e:
        logger.error(f"Error JS: {e}")
        return []

# ─────────────────────────────────────────────
# ESPERA ROBUSTA PARA QUE CARGUE EL FEED
# ─────────────────────────────────────────────

def esperar_feed(page, max_espera: int = 20) -> int:
    """
    Espera a que haya al menos 3 hijos con contenido en el feed.
    Devuelve cuántos hijos encontró.
    Hace scrolls pequeños para activar el lazy loading.
    """
    inicio = time.time()
    for intento in range(max_espera):
        hijos = page.evaluate("""
            () => {
                const feed = document.querySelector('div[role="feed"]');
                if (!feed) return 0;
                return Array.from(feed.children)
                    .filter(el => (el.innerText || '').trim().length > 30)
                    .length;
            }
        """)
        if hijos >= 2:
            logger.debug(f"Feed listo: {hijos} hijos con contenido ({intento+1}s)")
            return hijos
        # Scroll pequeño para activar lazy loading
        page.evaluate("window.scrollBy(0, 200)")
        time.sleep(1)

    logger.warning(f"Feed no cargó suficiente en {max_espera}s")
    return 0

# ─────────────────────────────────────────────
# SCROLL LOOP
# ─────────────────────────────────────────────

def scroll_y_extraer(page, grupo: dict) -> list:
    todos = []
    claves = set()
    sin_nuevos = 0

    for i in range(MAX_SCROLLS):
        # Expandir "Ver más"
        click_ver_mas(page)
        time.sleep(0.5)

        # Extraer
        nuevos = extraer(page, grupo)
        agregados = 0
        for p in nuevos:
            k = p["url_post"] or p["descripcion"][:120].strip()
            if k in claves: continue
            claves.add(k)
            todos.append(p)
            agregados += 1

        print(f"  Scroll {i+1:>2}: {len(todos):>4} posts (+{agregados} nuevos)")

        if agregados == 0:
            sin_nuevos += 1
            if sin_nuevos >= 5:
                print("  ⏹ 5 scrolls sin nuevos — terminando grupo")
                break
        else:
            sin_nuevos = 0

        # Guardado parcial cada 10 scrolls
        if (i+1) % 10 == 0 and todos:
            guardar_json(todos, grupo)
            print(f"  💾 Parcial guardado: {len(todos)} posts")

        # Scroll
        try:
            # Scroll gradual en 3 pasos para activar lazy loading correctamente
            page.evaluate("window.scrollBy(0, window.innerHeight * 0.5)")
            time.sleep(0.8)
            page.evaluate("window.scrollBy(0, window.innerHeight * 0.5)")
            time.sleep(0.8)
            page.evaluate("window.scrollBy(0, window.innerHeight * 0.5)")
            time.sleep(random.uniform(SCROLL_DELAY_MIN, SCROLL_DELAY_MAX))
        except Exception as e:
            logger.warning(f"Scroll error: {e}"); break

    return todos

# ─────────────────────────────────────────────
# GUARDAR
# ─────────────────────────────────────────────

def guardar_json(posts: list, grupo: dict):
    if not posts: return
    nombre = re.sub(r'[^a-z0-9]', '_', grupo["nombre"].lower())
    path = OUTPUT_DIR / f"grupo_{grupo['id']}_{nombre}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(posts, f, ensure_ascii=False, indent=2)
    logger.info(f"Guardado: {path.name} ({len(posts)} posts)")

# ─────────────────────────────────────────────
# SCRAPE GRUPO
# ─────────────────────────────────────────────

def scrape_grupo(grupo: dict, page) -> list:
    url = f"https://www.facebook.com/groups/{grupo['id']}"
    print(f"\n{'─'*55}")
    print(f"  Grupo: {grupo['nombre']}")
    print(f"  URL:   {url}")
    print(f"{'─'*55}")

    try:
        page.goto(url, timeout=60000, wait_until="domcontentloaded")

        # Esperar a que el feed tenga contenido real
        print("  ⏳ Esperando que cargue el feed...")
        n = esperar_feed(page, max_espera=25)
        print(f"  ✔  Feed listo: {n} posts visibles")

        if n == 0:
            print("  ⚠️  Feed vacío — saltando grupo")
            try:
                page.screenshot(path=OUTPUT_DIR / f"debug_vacio_{grupo['id']}.png")
            except: pass
            return []

        html = page.content().lower()
        if "no estás en este grupo" in html or "join group" in html:
            print("  ⚠️  No eres miembro — saltando")
            return []

    except Exception as e:
        print(f"  ❌ Error cargando grupo: {e}")
        return []

    posts = scroll_y_extraer(page, grupo)

    if posts:
        guardar_json(posts, grupo)
        print(f"\n  ✅ {grupo['nombre']}: {len(posts)} posts guardados")
    else:
        print(f"\n  ⚠️ {grupo['nombre']}: 0 posts relevantes")
        try:
            page.screenshot(path=OUTPUT_DIR / f"debug_vacio_{grupo['id']}.png")
        except: pass

    return posts

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    print("\n" + "="*55)
    print("  CUBACOMIDA — SCRAPER FACEBOOK v8")
    print("="*55)
    print(f"  Grupos:  {len(GRUPOS)}")
    print(f"  Datos:   {OUTPUT_DIR}")
    print("="*55)

    prog = cargar_progreso()
    completados = set(prog.get("completados", []))
    if completados:
        print(f"\n  ♻️  Ya procesados: {len(completados)}  |  Pendientes: {len(GRUPOS)-len(completados)}")

    with sync_playwright() as p:

        # ── LOGIN ──────────────────────────────────────────
        if not sesion_existe():
            if not hacer_login(p):
                print("❌ Login fallido"); return
        else:
            print("\n✅ Verificando sesión...")
            browser, ctx = nuevo_browser(p, headless=False)
            cargar_cookies(ctx)
            page = ctx.new_page()
            try:
                page.goto("https://www.facebook.com", timeout=45000, wait_until="domcontentloaded")
                time.sleep(4)
                if not esta_logueado(page):
                    print("⚠️  Sesión expirada — login de nuevo")
                    ctx.close(); browser.close(); borrar_sesion()
                    if not hacer_login(p): return
                else:
                    print("✅ Sesión válida")
                    ctx.close(); browser.close()
            except Exception as e:
                print(f"⚠️  {e}"); ctx.close(); browser.close()

        # ── SCRAPING ───────────────────────────────────────
        print("\n🚀 Iniciando scraping (modo visible)...")
        browser, ctx = nuevo_browser(p, headless=False)
        if not cargar_cookies(ctx):
            print("❌ Sin cookies"); browser.close(); return

        page = ctx.new_page()
        try:
            page.goto("https://www.facebook.com", timeout=45000, wait_until="domcontentloaded")
            time.sleep(4)
            print("✅ Facebook cargado")
        except Exception as e:
            print(f"❌ {e}"); browser.close(); return

        total = 0
        resultados = {}

        for idx, grupo in enumerate(GRUPOS):
            gid = grupo["id"]
            if gid in completados:
                print(f"\n  ⏭️  Ya procesado: {grupo['nombre']}"); continue
            try:
                posts = scrape_grupo(grupo, page)
                resultados[gid] = len(posts)
                total += len(posts)
                completados.add(gid)
                prog["completados"] = list(completados)
                prog["ultima_actualizacion"] = datetime.now().isoformat()
                guardar_progreso(prog)
            except Exception as e:
                logger.error(f"Error {grupo['nombre']}: {e}")
                print(f"  ❌ {e}")

            if idx < len(GRUPOS)-1:
                pausa = random.uniform(10, 20)
                print(f"\n  ⏳ Pausa {pausa:.0f}s antes del siguiente grupo...")
                time.sleep(pausa)

        try: ctx.close(); browser.close()
        except: pass

        # ── RESUMEN ────────────────────────────────────────
        print("\n" + "="*55)
        print("  RESUMEN FINAL")
        print("="*55)
        print(f"  Total posts extraídos: {total}")
        for g in GRUPOS:
            n = resultados.get(g["id"], "↩ ya procesado" if g["id"] in completados else 0)
            print(f"    {g['nombre'][:42]:<44} {n}")
        print(f"\n  📁 {OUTPUT_DIR}")
        print("="*55)


if __name__ == "__main__":
    main()