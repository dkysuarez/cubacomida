"""
fb_debug.py — Diagnóstico: qué renderiza Facebook en un grupo
Corre esto PRIMERO para saber qué selectores funcionan en tu máquina.
Guarda HTML + reporte en la carpeta de datos.
"""

import json, time
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_DIR     = Path(__file__).resolve().parent.parent
OUTPUT_DIR   = BASE_DIR / "data" / "raw" / "facebook"
COOKIES_FILE = BASE_DIR / "facebook_cookies.json"
CHROMIUM_EXE = r"D:\CubaComida\cubacomida\.browsers\chromium-1208\chrome-win64\chrome.exe"
GRUPO_TEST   = "1445123576384993"   # cambia si quieres probar otro

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=CHROMIUM_EXE,
            headless=False,
            args=["--no-sandbox","--disable-blink-features=AutomationControlled","--window-size=1366,900"]
        )
        ctx = browser.new_context(
            viewport={"width":1366,"height":900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            locale="es-ES",
        )
        ctx.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")

        if not COOKIES_FILE.exists():
            print("❌ No hay cookies. Corre el scraper primero para hacer login."); browser.close(); return
        with open(COOKIES_FILE) as f:
            ctx.add_cookies(json.load(f))

        page = ctx.new_page()
        print(f"Abriendo grupo {GRUPO_TEST}...")
        page.goto(f"https://www.facebook.com/groups/{GRUPO_TEST}", timeout=60000, wait_until="domcontentloaded")
        time.sleep(6)

        page.screenshot(path=OUTPUT_DIR/"debug_inicial.png")
        print("📸 Screenshot inicial guardado")

        html = page.content()
        with open(OUTPUT_DIR/"debug_grupo.html","w",encoding="utf-8") as f:
            f.write(html)
        print(f"💾 HTML guardado ({len(html)//1024} KB)")

        print("\n─── SELECTORES ───")
        sels = {
            "role=article":         'div[role="article"]',
            "FeedUnit":             'div[data-pagelet^="FeedUnit"]',
            "role=feed":            'div[role="feed"]',
            "feed > div (hijos)":   'div[role="feed"] > div',
            "dir=auto":             'div[dir="auto"]',
            "aria-posinset":        '[aria-posinset]',
            "data-ad-comet":        '[data-ad-comet-preview="message"]',
            "data-ad-preview":      '[data-ad-preview="message"]',
        }
        for nombre, sel in sels.items():
            try:
                n = len(page.query_selector_all(sel))
                print(f"  {nombre:<30} → {n:>4}  ({sel})")
            except Exception as e:
                print(f"  {nombre:<30} → ERROR: {e}")

        print("\n─── HIJOS DEL FEED (primeros 3) ───")
        hijos = page.query_selector_all('div[role="feed"] > div')
        for i, h in enumerate(hijos[:3]):
            t = (h.inner_text() or "").strip()[:400]
            print(f"\n[Hijo {i+1}] {len(t)} chars\n{t!r}")

        print("\n⬇️  Scrolleando 4 veces...")
        for _ in range(4):
            page.evaluate("window.scrollBy(0,window.innerHeight)")
            time.sleep(2)
        page.screenshot(path=OUTPUT_DIR/"debug_tras_scroll.png")
        print("📸 Screenshot tras scroll guardado")

        print("\n─── ARTÍCULOS TRAS SCROLL ───")
        arts = page.query_selector_all('div[role="article"]')
        print(f"Total: {len(arts)}")
        for i, art in enumerate(arts[:4]):
            t = (art.inner_text() or "").strip()[:400]
            print(f"\n[Art {i+1}] {len(t)} chars\n{t!r}")

        print(f"\n✅ Debug listo. Archivos en:\n   {OUTPUT_DIR}")
        input("\nPresiona ENTER para cerrar el browser...")
        browser.close()

if __name__ == "__main__":
    main()