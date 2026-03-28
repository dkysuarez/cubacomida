# 🇨🇺 CubaComida — Analizador de Precios de Alimentos en La Habana

Scraper + base de datos + dashboard para monitorear precios de comida en grupos de Facebook y tiendas online cubanas.

---

## Estructura del proyecto

```
cubacomida/
├── scrapers/
│   ├── facebook_scraper.py   ← Scraper de grupos de Facebook (Playwright)
│   └── limpiador.py          ← Limpieza, categorización y carga a SQLite
├── data/
│   ├── raw/facebook/         ← JSONs crudos del scraper
│   └── cubacomida.db         ← Base de datos SQLite
├── logs/
│   └── facebook_scraper.log
├── requirements.txt
└── README.md
```

---

## Setup

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Instalar Playwright y el navegador
playwright install chromium

# 3. Crear directorios
mkdir -p data/raw/facebook logs
```

---

## Uso

### 1. Scrapear Facebook

```bash
python scrapers/facebook_scraper.py
```

- Se abrirá una ventana de Chromium con Facebook
- Inicia sesión manualmente (tienes 3 minutos)
- El scraper iterará por los 20 grupos automáticamente
- Los JSONs crudos se guardan en `data/raw/facebook/`

### 2. Limpiar y cargar a SQLite

```bash
# Procesar todos los JSONs en data/raw/facebook/
python scrapers/limpiador.py

# O procesar un archivo específico
python scrapers/limpiador.py data/raw/facebook/facebook_raw_20240325_143000.json
```

---

## Campos extraídos por anuncio

| Campo | Descripción |
|-------|-------------|
| `titulo` | Primeras 200 chars del post |
| `descripcion` | Texto completo |
| `precio` | Número extraído |
| `moneda` | USD / MLC / CUP |
| `precio_usd` | Precio normalizado a USD |
| `unidad` | libra / kg / caja / combo / etc. |
| `cantidad` | Número de unidades |
| `categoria` | Categoría detectada automáticamente |
| `mayorista` | True si es venta mayorista |
| `telefono` | Número de contacto |
| `whatsapp` | Número de WhatsApp |
| `vendedor` | Nombre del autor |
| `fuente` | `facebook_grupo` o `tienda_online` |
| `fuente_nombre` | Nombre del grupo/tienda |
| `url` | Link al post |
| `provincia` | La Habana (default) |
| `fecha_post` | Fecha original del anuncio |
| `fecha_scraping` | Timestamp del scraping |

---

## Categorías

| Clave | Nombre visible |
|-------|---------------|
| `pollo` | Pollo y Cárnicos de Aves |
| `carne` | Carne de Res |
| `cerdo` | Cerdo y Embutidos |
| `picadillo` | Picadillo y Perrito |
| `mariscos` | Pescado y Mariscos |
| `lacteos` | Lácteos |
| `huevos` | Huevos |
| `arroz` | Arroz y Granos |
| `harina` | Harina, Pan y Pastas |
| `azucar` | Azúcar y Dulces |
| `aceite` | Aceite y Condimentos |
| `vegetales` | Vegetales y Viandas |
| `frutas` | Frutas |
| `galletas` | Galletas y Snacks |
| `bebidas` | Bebidas y Jugos |
| `conservas` | Conservas y Enlatados |
| `combos` | Combos y Paquetes mixtos |
| `mayorista` | Venta Mayorista |
| `otros` | Otros alimentos |

---

## Tasas de cambio (actualizar en `limpiador.py`)

```python
TASAS = {
    "USD": 1.0,
    "MLC": 1.0,
    "CUP": 1 / 340,  # Actualizar según tasa del mercado informal
}
```

---

## Próximos pasos

- [ ] Scraper de tiendas online (Supermarket23, TiendaHabana, etc.)
- [ ] Dashboard Streamlit con filtros por categoría, precio, fuente
- [ ] Alertas de precios bajos
- [ ] Histórico de precios con gráficas Plotly