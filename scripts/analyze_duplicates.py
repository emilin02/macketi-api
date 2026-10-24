# ============================================================
# SCRIPT DE ANÁLISIS DE DUPLICADOS
# ============================================================
# Lee el JSON exportado de WooCommerce y genera dos CSV:
#
# 1. duplicates_review.csv
#    Lista los grupos de productos que comparten el mismo
#    nombre normalizado. Sirve para revisar a mano qué
#    agrupar y qué no.
#
# 2. stores_mapping.csv
#    Mapea cada post_author (ID de WordPress) con la tienda
#    de Dokan correspondiente.
#
# Uso:
#   python scripts/analyze_duplicates.py

import csv
import json
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

# Añadimos la raíz del proyecto al path
sys.path.insert(0, str(Path(__file__).parent.parent))


# ============================================================
# RUTAS
# ============================================================

DATA_DIR = Path(__file__).parent.parent / "data"
INPUT_FILE = DATA_DIR / "woocommerce_export.json"
DUPLICATES_OUTPUT = DATA_DIR / "duplicates_review.csv"
STORES_OUTPUT = DATA_DIR / "stores_mapping.csv"


# ============================================================
# NORMALIZACIÓN DE NOMBRES
# ============================================================

def normalize_name(name: str) -> str:
    """
    Normaliza un nombre para comparación:
    - Pasa a minúsculas.
    - Quita tildes y diacríticos.
    - Quita signos de puntuación.
    - Colapsa espacios múltiples.
    - Quita espacios al principio y final.
    """
    # Descomponer caracteres Unicode (á → a + ́)
    nfd = unicodedata.normalize("NFD", name.lower())
    # Eliminar diacríticos (marcas combinantes)
    without_accents = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
    # Reemplazar signos de puntuación por espacios
    cleaned = re.sub(r"[^\w\s]", " ", without_accents)
    # Colapsar espacios
    collapsed = re.sub(r"\s+", " ", cleaned)
    return collapsed.strip()


# ============================================================
# HELPERS
# ============================================================

def extract_category_name(product: dict) -> str:
    """Devuelve el nombre de la primera categoría o cadena vacía."""
    cats = product.get("categories") or []
    return cats[0]["name"] if cats else ""


def parse_price(product: dict) -> float:
    """Convierte el precio a float. Devuelve 0 si no hay."""
    try:
        return float(product.get("price") or 0)
    except (ValueError, TypeError):
        return 0.0


def get_post_author(product: dict) -> int:
    """Devuelve el post_author o 0 si no existe."""
    return product.get("post_author") or 0


# ============================================================
# ANÁLISIS PRINCIPAL
# ============================================================

def main() -> None:
    print("=" * 60)
    print("ANÁLISIS DE DUPLICADOS")
    print("=" * 60)
    print()

    # 1. Cargar el JSON.
    if not INPUT_FILE.exists():
        print(f"❌ No se encontró {INPUT_FILE}")
        print("   Ejecuta primero: python scripts/export_woocommerce.py")
        return

    print(f"📖 Leyendo {INPUT_FILE}...")
    data = json.loads(INPUT_FILE.read_text(encoding="utf-8"))
    products = data["products"]
    stores = data["stores"]

    print(f"   {len(products)} productos, {len(stores)} tiendas")
    print()

    # 2. Mapeo de post_author → store_name (de Dokan).
    #    El post_author de un producto es el ID del vendedor.
    #    El ID de tienda en Dokan coincide con el ID del usuario.
    stores_by_id = {s["id"]: s for s in stores}

    def store_name_for_author(author_id: int) -> str:
        """Devuelve el nombre de la tienda para un post_author."""
        store = stores_by_id.get(author_id)
        if not store:
            return f"Desconocida ({author_id})"
        name = store.get("store_name") or ""
        if name.strip():
            return name
        # Fallback: nombre + apellido
        first = store.get("first_name") or ""
        last = store.get("last_name") or ""
        full = f"{first} {last}".strip()
        return full or f"Sin nombre ({author_id})"

    # 3. Agrupar productos por nombre normalizado.
    print("🔍 Agrupando productos por nombre normalizado...")
    groups: dict[str, list[dict]] = defaultdict(list)

    for product in products:
        normalized = normalize_name(product.get("name", ""))
        if not normalized:
            continue
        groups[normalized].append(product)

    # 4. Filtrar solo los grupos con más de 1 producto (duplicados).
    duplicate_groups = {name: items for name, items in groups.items() if len(items) > 1}

    print(f"   {len(groups)} nombres únicos")
    print(f"   {len(duplicate_groups)} grupos con duplicados")
    print(f"   {sum(len(v) for v in duplicate_groups.values())} productos duplicados")
    print()

    # 5. Generar CSV de revisión.
    print(f"📝 Generando {DUPLICATES_OUTPUT}...")

    with DUPLICATES_OUTPUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "grupo_id",
            "nombre_normalizado",
            "grupo_tamaño",
            "woo_id",
            "nombre_original",
            "categoria",
            "precio",
            "tipo",
            "stock_status",
            "post_author",
            "tienda",
            "tiene_imagen",
            "slug",
            "decision",
        ])

        for group_id, (normalized, items) in enumerate(duplicate_groups.items(), start=1):
            # Ordenar por precio para ver diferencias más rápido
            items_sorted = sorted(items, key=parse_price)

            for product in items_sorted:
                writer.writerow([
                    group_id,
                    normalized,
                    len(items),
                    product.get("id"),
                    product.get("name", ""),
                    extract_category_name(product),
                    product.get("price", ""),
                    product.get("type", ""),
                    product.get("stock_status", ""),
                    get_post_author(product),
                    store_name_for_author(get_post_author(product)),
                    "SÍ" if product.get("images") else "NO",
                    product.get("slug", ""),
                    "",  # Columna vacía para que tú decidas: agrupar / separar
                ])

    # 6. Generar CSV de tiendas.
    print(f"📝 Generando {STORES_OUTPUT}...")

    with STORES_OUTPUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "dokan_id",
            "store_name",
            "first_name",
            "last_name",
            "shop_url",
            "vertical",
            "registered",
            "productos_count",
        ])

        # Contar productos por tienda
        product_count_by_author: dict[int, int] = defaultdict(int)
        for product in products:
            product_count_by_author[get_post_author(product)] += 1

        for store in stores:
            sid = store["id"]
            cats = store.get("categories") or []
            vertical = cats[0]["name"] if cats else ""

            writer.writerow([
                sid,
                store.get("store_name", ""),
                store.get("first_name", ""),
                store.get("last_name", ""),
                store.get("shop_url", ""),
                vertical,
                store.get("registered", ""),
                product_count_by_author.get(sid, 0),
            ])

    # 7. Reporte.
    print()
    print("=" * 60)
    print("✅ ANÁLISIS COMPLETADO")
    print("=" * 60)
    print(f"Grupos duplicados:          {len(duplicate_groups)}")
    print(f"Productos en esos grupos:   {sum(len(v) for v in duplicate_groups.values())}")
    print(f"Productos únicos totales:   {len(groups)}")
    print()
    print(f"CSV de revisión:  {DUPLICATES_OUTPUT}")
    print(f"CSV de tiendas:   {STORES_OUTPUT}")
    print()
    print("Siguiente paso:")
    print("  1. Abre el CSV de revisión en Excel.")
    print("  2. Revisa cada grupo y decide en la columna 'decision':")
    print("     - Escribe 'agrupar' si todos son el mismo producto.")
    print("     - Escribe 'separar' si son productos distintos.")
    print("  3. Guarda el CSV y avísame para el siguiente script.")
    print()


if __name__ == "__main__":
    main()