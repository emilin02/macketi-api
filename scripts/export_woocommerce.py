# ============================================================
# SCRIPT DE EXPORTACIÓN DE WOOCOMMERCE
# ============================================================
# Descarga TODOS los datos de WooCommerce y Dokan y los guarda
# en un JSON local para procesarlos después.
#
# Es un script de SOLO LECTURA. No modifica nada en WooCommerce.
#
# Uso:
#   python scripts/export_woocommerce.py
#
# Salida:
#   data/woocommerce_export.json

import asyncio
import json
import sys
from base64 import b64encode
from datetime import datetime, timezone
from pathlib import Path

import httpx

# Añadimos la raíz del proyecto al path para importar app.core.config
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings  # noqa: E402


# ============================================================
# CONFIGURACIÓN
# ============================================================

DATA_DIR = Path(__file__).parent.parent / "data"
OUTPUT_FILE = DATA_DIR / "woocommerce_export.json"

# WooCommerce limita las respuestas a 100 items por página.
PER_PAGE = 100

# Timeout para cada petición HTTP (segundos).
# Algunos productos con muchas variaciones tardan.
TIMEOUT = 60.0


# ============================================================
# CLIENTE HTTP CON AUTENTICACIÓN
# ============================================================

def build_auth_header() -> str:
    """Construye el header Basic Auth para WooCommerce."""
    raw = f"{settings.WOOCOMMERCE_CONSUMER_KEY}:{settings.WOOCOMMERCE_CONSUMER_SECRET}"
    encoded = b64encode(raw.encode()).decode()
    return f"Basic {encoded}"


def build_client() -> httpx.AsyncClient:
    """Crea un cliente HTTP async con autenticación preconfigurada."""
    return httpx.AsyncClient(
        base_url=f"{settings.WOOCOMMERCE_URL}/wp-json",
        headers={
            "Authorization": build_auth_header(),
            "Content-Type": "application/json",
        },
        timeout=TIMEOUT,
    )


# ============================================================
# HELPERS DE PAGINACIÓN
# ============================================================

async def fetch_paginated(
    client: httpx.AsyncClient,
    endpoint: str,
    params: dict | None = None,
) -> list[dict]:
    """
    Descarga TODAS las páginas de un endpoint paginado.

    WooCommerce devuelve las cabeceras X-WP-Total y X-WP-TotalPages,
    pero para simplicidad iteramos hasta que una página devuelva
    menos items que PER_PAGE.
    """
    all_items: list[dict] = []
    page = 1
    base_params = params or {}

    while True:
        request_params = {**base_params, "page": page, "per_page": PER_PAGE}
        print(f"  → {endpoint} página {page}...", end="", flush=True)

        response = await client.get(endpoint, params=request_params)
        response.raise_for_status()

        items = response.json()
        count = len(items)
        print(f" {count} items", flush=True)

        if count == 0:
            break

        all_items.extend(items)

        # Si esta página vino incompleta, era la última.
        if count < PER_PAGE:
            break

        page += 1

    return all_items


# ============================================================
# EXPORTADORES POR RECURSO
# ============================================================

async def export_products(client: httpx.AsyncClient) -> list[dict]:
    """Descarga todos los productos con post_author incluido."""
    print("📦 Exportando productos...")
    return await fetch_paginated(
        client,
        "/wc/v3/products",
        params={
            "status": "publish",
            # _fields nos limita lo que devuelve WooCommerce.
            # Incluimos TODO lo que necesitamos para la transformación.
            "_fields": ",".join([
                "id", "name", "slug", "permalink", "type", "status",
                "featured", "description", "short_description", "sku",
                "price", "regular_price", "sale_price", "on_sale",
                "stock_quantity", "stock_status",
                "categories", "tags", "images", "attributes",
                "variations", "average_rating", "rating_count",
                "date_created", "date_modified", "post_author",
            ]),
        },
    )


async def export_variations(
    client: httpx.AsyncClient,
    product_id: int,
) -> list[dict]:
    """Descarga las variaciones de un producto variable."""
    response = await client.get(
        f"/wc/v3/products/{product_id}/variations",
        params={"per_page": 100},
    )
    response.raise_for_status()
    return response.json()


async def export_categories(client: httpx.AsyncClient) -> list[dict]:
    """Descarga todas las categorías de producto."""
    print("📂 Exportando categorías...")
    return await fetch_paginated(
        client,
        "/wc/v3/products/categories",
        params={"hide_empty": False},
    )


async def export_tags(client: httpx.AsyncClient) -> list[dict]:
    """Descarga todas las etiquetas de producto."""
    print("🏷️  Exportando etiquetas...")
    return await fetch_paginated(client, "/wc/v3/products/tags")


async def export_dokan_stores(client: httpx.AsyncClient) -> list[dict]:
    """
    Descarga todas las tiendas de Dokan.
    Endpoint público (no requiere autenticación).
    """
    print("🏪 Exportando tiendas de Dokan...")

    all_stores: list[dict] = []
    page = 1

    while True:
        print(f"  → stores página {page}...", end="", flush=True)
        response = await client.get(
            f"{settings.DOKAN_API_URL}/stores",
            params={"page": page, "per_page": PER_PAGE},
        )
        response.raise_for_status()

        stores = response.json()
        print(f" {len(stores)} items", flush=True)

        if not stores:
            break

        all_stores.extend(stores)

        if len(stores) < PER_PAGE:
            break

        page += 1

    return all_stores


# ============================================================
# EJECUCIÓN PRINCIPAL
# ============================================================

async def main() -> None:
    """Ejecuta la exportación completa."""
    print("=" * 60)
    print("EXPORTACIÓN DE WOOCOMMERCE PARA MIGRACIÓN A MACKETI API")
    print("=" * 60)
    print()

    started_at = datetime.now(timezone.utc)

    async with build_client() as client:
        # 1. Productos.
        products = await export_products(client)

        # 2. Variaciones de productos variables.
        variable_products = [p for p in products if p.get("type") == "variable"]
        print(f"\n🔀 Exportando variaciones de {len(variable_products)} productos variables...")

        variations: dict[int, list[dict]] = {}
        for idx, product in enumerate(variable_products, start=1):
            pid = product["id"]
            print(f"  [{idx}/{len(variable_products)}] Producto {pid}...", end="", flush=True)
            try:
                product_variations = await export_variations(client, pid)
                variations[pid] = product_variations
                print(f" {len(product_variations)} variaciones", flush=True)
            except httpx.HTTPStatusError as e:
                print(f" ERROR {e.response.status_code}", flush=True)
                variations[pid] = []

        # 3. Categorías y etiquetas.
        categories = await export_categories(client)
        tags = await export_tags(client)

        # 4. Tiendas de Dokan.
        stores = await export_dokan_stores(client)

    # 5. Guardar todo en un solo JSON.
    output = {
        "metadata": {
            "exported_at": started_at.isoformat(),
            "woocommerce_url": settings.WOOCOMMERCE_URL,
            "counts": {
                "products": len(products),
                "variations": sum(len(v) for v in variations.values()),
                "categories": len(categories),
                "tags": len(tags),
                "stores": len(stores),
            },
        },
        "products": products,
        "variations": {str(k): v for k, v in variations.items()},
        "categories": categories,
        "tags": tags,
        "stores": stores,
    }

    DATA_DIR.mkdir(exist_ok=True)
    OUTPUT_FILE.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # 6. Reporte final.
    elapsed = (datetime.now(timezone.utc) - started_at).total_seconds()

    print()
    print("=" * 60)
    print("✅ EXPORTACIÓN COMPLETADA")
    print("=" * 60)
    print(f"Productos:    {len(products)}")
    print(f"Variaciones:  {sum(len(v) for v in variations.values())}")
    print(f"Categorías:   {len(categories)}")
    print(f"Etiquetas:    {len(tags)}")
    print(f"Tiendas:      {len(stores)}")
    print(f"Tiempo:       {elapsed:.1f} segundos")
    print(f"Archivo:      {OUTPUT_FILE}")
    print()


if __name__ == "__main__":
    asyncio.run(main())