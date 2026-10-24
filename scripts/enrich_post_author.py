# ============================================================
# SCRIPT DE ENRIQUECIMIENTO: post_author vía Dokan
# ============================================================
# La API de WooCommerce NO devuelve post_author.
# La API pública de WordPress tampoco (está oculto).
# Pero la API de Dokan SÍ lo devuelve en:
#   /wp-json/dokan/v1/stores/{store_id}/products
#
# Este script:
# 1. Lee el JSON exportado de WooCommerce.
# 2. Recorre las 60 tiendas de Dokan.
# 3. Para cada tienda, pide sus productos (paginados).
# 4. Construye un mapa {product_id: post_author}.
# 5. Enriquece el JSON con ese campo.
#
# Uso:
#   python scripts/enrich_post_author.py

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings  # noqa: E402


# ============================================================
# RUTAS
# ============================================================

DATA_DIR = Path(__file__).parent.parent / "data"
INPUT_FILE = DATA_DIR / "woocommerce_export.json"
OUTPUT_FILE = DATA_DIR / "woocommerce_export_enriched.json"


# ============================================================
# CONFIGURACIÓN
# ============================================================

PER_PAGE = 100
TIMEOUT = 60.0


# ============================================================
# CONSULTA A DOKAN
# ============================================================

async def fetch_products_for_store(
    client: httpx.AsyncClient,
    store_id: int,
) -> dict[int, int]:
    """
    Pide todos los productos de una tienda de Dokan.
    Devuelve un dict {product_id: store_id} (o sea, post_author).
    """
    result: dict[int, int] = {}
    page = 1

    while True:
        response = await client.get(
            f"{settings.DOKAN_API_URL}/stores/{store_id}/products",
            params={"per_page": PER_PAGE, "page": page},
        )
        response.raise_for_status()

        products = response.json()
        if not products:
            break

        for product in products:
            result[product["id"]] = store_id

        if len(products) < PER_PAGE:
            break

        page += 1

    return result


# ============================================================
# EJECUCIÓN PRINCIPAL
# ============================================================

async def main() -> None:
    print("=" * 60)
    print("ENRIQUECIMIENTO: post_author vía Dokan")
    print("=" * 60)
    print()

    if not INPUT_FILE.exists():
        print(f"❌ No se encontró {INPUT_FILE}")
        print("   Ejecuta primero: python scripts/export_woocommerce.py")
        return

    print(f"📖 Leyendo {INPUT_FILE}...")
    data = json.loads(INPUT_FILE.read_text(encoding="utf-8"))

    products = data["products"]
    stores = data["stores"]

    print(f"   {len(products)} productos")
    print(f"   {len(stores)} tiendas")
    print()

    # Ordenar tiendas por ID para tener un orden predecible
    stores_sorted = sorted(stores, key=lambda s: s["id"])

    print(f"🔍 Consultando productos de cada tienda de Dokan...")
    print()

    # Mapa global {product_id: post_author}
    product_to_author: dict[int, int] = {}

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        for idx, store in enumerate(stores_sorted, start=1):
            store_id = store["id"]
            store_name = store.get("store_name") or f"Tienda {store_id}"

            print(f"   [{idx:2d}/{len(stores_sorted)}] Tienda {store_id} ({store_name[:30]})...", end="", flush=True)

            try:
                store_products = await fetch_products_for_store(client, store_id)
                product_to_author.update(store_products)
                print(f" {len(store_products)} productos", flush=True)
            except httpx.HTTPStatusError as e:
                print(f" ERROR {e.response.status_code}", flush=True)
            except Exception as e:
                print(f" ERROR: {e}", flush=True)

    print()
    print(f"   Total productos mapeados: {len(product_to_author)}")
    print()

    # Aplicar a los productos
    print("✏️  Aplicando post_author a los productos...")
    enriched = 0
    missing = 0

    for product in products:
        pid = product["id"]
        if pid in product_to_author:
            product["post_author"] = product_to_author[pid]
            enriched += 1
        else:
            product["post_author"] = None
            missing += 1

    print(f"   Productos enriquecidos: {enriched}")
    print(f"   Productos sin autor:    {missing}")
    print()

    # Guardar
    data["metadata"]["enriched_at"] = datetime.now(timezone.utc).isoformat()
    data["metadata"]["enriched_via"] = "dokan"

    OUTPUT_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("=" * 60)
    print("✅ ENRIQUECIMIENTO COMPLETADO")
    print("=" * 60)
    print(f"Archivo: {OUTPUT_FILE}")
    print()


if __name__ == "__main__":
    asyncio.run(main())