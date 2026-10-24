# ============================================================
# SCRIPT DE TRANSFORMACIÓN
# ============================================================
# Lee el JSON exportado de WooCommerce y genera un JSON con la
# estructura de la nueva API (Product + Offer).
#
# Reglas de agrupación automática:
# 1. Mismo nombre normalizado.
# 2. Misma categoría principal.
# 3. Precio dentro del ±30% del precio medio del grupo.
#
# Uso:
#   python scripts/transform_woocommerce.py
#
# Salida:
#   data/macketi_products.json

import json
import re
import sys
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


# ============================================================
# RUTAS
# ============================================================

DATA_DIR = Path(__file__).parent.parent / "data"
INPUT_FILE = DATA_DIR / "woocommerce_export_enriched.json"
OUTPUT_FILE = DATA_DIR / "macketi_products.json"


# ============================================================
# NORMALIZACIÓN
# ============================================================

def normalize_name(name: str) -> str:
    """Normaliza un nombre para comparación."""
    nfd = unicodedata.normalize("NFD", name.lower())
    without_accents = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
    cleaned = re.sub(r"[^\w\s]", " ", without_accents)
    collapsed = re.sub(r"\s+", " ", cleaned)
    return collapsed.strip()


def slugify(name: str) -> str:
    """Genera un slug a partir de un nombre."""
    nfd = unicodedata.normalize("NFD", name.lower())
    without_accents = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
    cleaned = re.sub(r"[^\w\s-]", "", without_accents)
    cleaned = re.sub(r"[\s_]+", "-", cleaned)
    cleaned = re.sub(r"-+", "-", cleaned)
    return cleaned.strip("-")[:200]


def parse_price(value) -> float:
    """Convierte un precio a float."""
    try:
        return float(value or 0)
    except (ValueError, TypeError):
        return 0.0


def parse_int(value) -> int:
    """Convierte un valor a int."""
    try:
        return int(value or 0)
    except (ValueError, TypeError):
        return 0


def strip_html(html: str | None) -> str:
    """Quita etiquetas HTML de un texto."""
    if not html:
        return ""
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# ============================================================
# TRANSFORMACIÓN DE CATEGORÍAS
# ============================================================

def transform_categories(woo_categories: list[dict]) -> list[dict]:
    """
    Convierte las categorías de WooCommerce al formato de la API.
    WooCommerce devuelve `parent` (ID), nosotros lo mapeamos.
    """
    result = []
    for cat in woo_categories:
        result.append({
            "woo_id": cat["id"],
            "slug": cat["slug"],
            "name": cat["name"],
            "parent_woo_id": cat.get("parent") or None,
            "description": strip_html(cat.get("description")),
            "image_url": cat.get("image", {}).get("src") if cat.get("image") else None,
            "position": cat.get("menu_order", 0),
            "is_active": True,
        })
    return result


# ============================================================
# TRANSFORMACIÓN DE TIENDAS (DOKAN)
# ============================================================

def transform_stores(woo_stores: list[dict]) -> list[dict]:
    """
    Convierte las tiendas de Dokan al formato de la API.

    Nota: el campo `id` de Dokan coincide con el `post_author` de
    los productos. Por eso los usamos como referencia.
    """
    result = []
    for store in woo_stores:
        # Vertical: viene en `categories[0].name`
        cats = store.get("categories") or []
        vertical = cats[0]["slug"] if cats else "tienda"

        # Email: no siempre está público
        email = store.get("email") or None

        result.append({
            "dokan_id": store["id"],
            "slug": store.get("shop_url", "").rstrip("/").split("/")[-1] or f"store-{store['id']}",
            "name": store.get("store_name") or f"{store.get('first_name', '')} {store.get('last_name', '')}".strip() or f"Tienda {store['id']}",
            "description": strip_html(store.get("vendor_biography")) or None,
            "logo_url": store.get("gravatar") or None,
            "banner_url": store.get("banner") or None,
            "phone": store.get("phone") or None,
            "email": email,
            "vertical": vertical,
            "address": None,
            "city": None,  # no está en Dokan
            "is_active": True,
            "is_verified": False,  # se verificará manualmente después
            "rating_avg": float(store.get("rating", {}).get("rating", 0) or 0),
            "rating_count": int(store.get("rating", {}).get("count", 0) or 0),
            "total_orders": 0,
            "commission_pct": None,
        })
    return result


# ============================================================
# AGRUPACIÓN DE PRODUCTOS
# ============================================================

def build_grouping_key(product: dict) -> tuple[str, str]:
    """
    Clave de agrupación: nombre normalizado + categoría principal.
    """
    name = normalize_name(product.get("name", ""))
    cats = product.get("categories") or []
    category = cats[0]["slug"] if cats else ""
    return (name, category)


def filter_by_price_range(
    group: list[dict],
    jump_threshold: float = 0.50,
) -> list[list[dict]]:
    """
    Divide un grupo de productos en subgrupos según sus precios.

    Algoritmo (iterativo, sin recursión):
    1. Ordenar los productos por precio.
    2. Recorrer los precios de menor a mayor.
    3. Cada vez que el salto entre un precio y el siguiente sea
       mayor al `jump_threshold` (por defecto 50%), cortar y
       empezar un nuevo subgrupo.

    Ejemplo con jump_threshold=0.5:
        Precios: [15000, 16000, 50000, 52000, 150000]
        Saltos:     6.7%   212%   4%     188%
        Cortes:           ↑            ↑
        Subgrupos: [15000, 16000], [50000, 52000], [150000]

    Los productos con precio 0 se consideran "sin precio" y se
    agrupan todos juntos en un subgrupo aparte.
    """
    if len(group) <= 1:
        return [group]

    # Separar productos sin precio (precio == 0)
    with_price = []
    without_price = []

    for product in group:
        price = parse_price(product.get("price"))
        if price > 0:
            with_price.append((price, product))
        else:
            without_price.append(product)

    if not with_price:
        # Todos sin precio: un solo subgrupo
        return [group]

    # Ordenar por precio ascendente
    with_price.sort(key=lambda x: x[0])

    # Detectar saltos y cortar
    sub_groups: list[list[dict]] = []
    current_group: list[dict] = [with_price[0][1]]
    current_price = with_price[0][0]

    for price, product in with_price[1:]:
        # Calcular salto relativo
        if current_price > 0:
            jump = (price - current_price) / current_price
        else:
            jump = 0

        if jump > jump_threshold:
            # Cortar: empezar nuevo subgrupo
            sub_groups.append(current_group)
            current_group = [product]
        else:
            current_group.append(product)

        current_price = price

    # Añadir el último subgrupo
    sub_groups.append(current_group)

    # Si hay productos sin precio, meterlos en su propio subgrupo
    if without_price:
        sub_groups.append(without_price)

    return sub_groups


# ============================================================
# CONSTRUCCIÓN DE PRODUCTOS Y OFERTAS
# ============================================================

def build_products_and_offers(
    woo_products: list[dict],
    woo_stores_by_id: dict,
) -> tuple[list[dict], list[dict]]:
    """
    Agrupa productos y genera productos únicos + ofertas.
    """
    # 1. Agrupar por (nombre_normalizado, categoría)
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for product in woo_products:
        key = build_grouping_key(product)
        groups[key].append(product)

    products: list[dict] = []
    offers: list[dict] = []
    used_slugs: set[str] = set()

    for key, group in groups.items():
        normalized_name, category_slug = key

        # 2. Subdividir por rango de precio
        sub_groups = filter_by_price_range(group)

        for sub_index, sub_group in enumerate(sub_groups):
            # Producto representativo (el primero del subgrupo)
            representative = sub_group[0]

            # 3. Generar slug único
            base_slug = representative.get("slug") or slugify(representative["name"])
            if sub_index > 0:
                base_slug = f"{base_slug}-{sub_index + 1}"
            slug = base_slug
            counter = 2
            while slug in used_slugs:
                slug = f"{base_slug}-{counter}"
                counter += 1
            used_slugs.add(slug)

            # 4. Imagen principal
            images = representative.get("images") or []
            main_image = images[0]["src"] if images else None

            # 5. Producto
            products.append({
                "woo_id": representative["id"],  # referencia
                "slug": slug,
                "name": representative["name"],
                "description": representative.get("description") or None,
                "short_description": strip_html(representative.get("short_description")) or None,
                "category_woo_id": representative.get("categories", [{}])[0].get("id") if representative.get("categories") else None,
                "brand_woo_id": None,  # WooCommerce no tiene brands nativo, se mapearán después
                "main_image_url": main_image,
                "woo_type": representative.get("type"),
                "woo_sku": representative.get("sku") or None,
                "is_active": True,
                "approval_status": "approved",  # los productos existentes ya están aprobados
            })

            # 6. Ofertas (una por cada producto del subgrupo)
            for woo_product in sub_group:
                author_id = woo_product.get("post_author") or 0
                store = woo_stores_by_id.get(author_id)

                if not store:
                    # Si no hay tienda, no podemos crear la oferta
                    continue

                stock_qty = parse_int(woo_product.get("stock_quantity"))
                stock_unlimited = woo_product.get("stock_status") == "instock" and stock_qty == 0

                offers.append({
                    "woo_product_id": woo_product["id"],
                    "product_woo_id": representative["id"],
                    "store_dokan_id": author_id,
                    "price": parse_price(woo_product.get("price")),
                    "compare_price": parse_price(woo_product.get("regular_price")) or None,
                    "stock": stock_qty,
                    "stock_unlimited": stock_unlimited,
                    "condition": "new",
                    "status": "active" if woo_product.get("stock_status") == "instock" else "out_of_stock",
                    "sku": woo_product.get("sku") or None,
                    "requires_prescription": False,
                    "prep_time_min": None,
                })

    return products, offers


# ============================================================
# EJECUCIÓN PRINCIPAL
# ============================================================

def main() -> None:
    print("=" * 60)
    print("TRANSFORMACIÓN DE WOOCOMMERCE A MODELO AMAZON")
    print("=" * 60)
    print()

    if not INPUT_FILE.exists():
        print(f"❌ No se encontró {INPUT_FILE}")
        print("   Ejecuta primero: python scripts/export_woocommerce.py")
        return

    print(f"📖 Leyendo {INPUT_FILE}...")
    data = json.loads(INPUT_FILE.read_text(encoding="utf-8"))

    woo_products = data["products"]
    woo_categories = data["categories"]
    woo_stores = data["stores"]

    print(f"   {len(woo_products)} productos")
    print(f"   {len(woo_categories)} categorías")
    print(f"   {len(woo_stores)} tiendas")
    print()

    # 1. Transformar categorías y tiendas
    print("📂 Transformando categorías...")
    categories = transform_categories(woo_categories)
    print(f"   {len(categories)} categorías transformadas")

    print("🏪 Transformando tiendas...")
    stores = transform_stores(woo_stores)
    print(f"   {len(stores)} tiendas transformadas")
    print()

    # 2. Mapeo de tiendas por ID
    stores_by_id = {s["dokan_id"]: s for s in stores}

    # 3. Agrupar productos y generar ofertas
    print("🔀 Agrupando productos y generando ofertas...")
    products, offers = build_products_and_offers(woo_products, stores_by_id)
    print(f"   {len(products)} productos únicos generados")
    print(f"   {len(offers)} ofertas generadas")
    print()

    # 4. Guardar todo
    output = {
        "metadata": {
            "transformed_at": datetime.now(timezone.utc).isoformat(),
            "source": str(INPUT_FILE),
            "counts": {
                "categories": len(categories),
                "stores": len(stores),
                "products": len(products),
                "offers": len(offers),
            },
        },
        "categories": categories,
        "stores": stores,
        "products": products,
        "offers": offers,
    }

    OUTPUT_FILE.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # 5. Reporte final
    print("=" * 60)
    print("✅ TRANSFORMACIÓN COMPLETADA")
    print("=" * 60)
    print(f"Categorías:    {len(categories)}")
    print(f"Tiendas:       {len(stores)}")
    print(f"Productos:     {len(products)}")
    print(f"Ofertas:       {len(offers)}")
    print()
    print(f"Archivo:       {OUTPUT_FILE}")
    print()


if __name__ == "__main__":
    main()