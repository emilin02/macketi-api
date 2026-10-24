# ============================================================
# DIAGNÓSTICO: ¿Por qué no se generan ofertas?
# ============================================================

import json
from pathlib import Path

data = json.loads(Path("data/woocommerce_export.json").read_text(encoding="utf-8"))

# 1. IDs de tiendas Dokan
store_ids = {s["id"] for s in data["stores"]}
print(f"Total tiendas Dokan: {len(store_ids)}")
print(f"Primeros IDs de tiendas: {sorted(store_ids)[:20]}")
print()

# 2. Post_authors de productos
product_authors = {p.get("post_author") for p in data["products"] if p.get("post_author")}
print(f"Post_authors únicos en productos: {len(product_authors)}")
print(f"Primeros post_authors: {sorted(product_authors)[:20]}")
print()

# 3. ¿Cuántos coinciden?
matching = product_authors & store_ids
no_match = product_authors - store_ids
print(f"Post_authors que SÍ coinciden con tiendas: {len(matching)}")
print(f"Post_authors que NO coinciden: {len(no_match)}")
print()

# 4. Ejemplos concretos
print("Primeros 5 productos:")
for p in data["products"][:5]:
    print(f"  Producto ID {p['id']}: post_author={p.get('post_author')}, name={p['name'][:50]}")
print()

print("Primeras 5 tiendas:")
for s in data["stores"][:5]:
    name = s.get("store_name") or "(sin nombre)"
    url = s.get("shop_url") or ""
    print(f"  Tienda ID {s['id']}: name={name}, shop_url={url}")
print()

# 5. ¿Cuántos productos tienen post_author?
con_author = sum(1 for p in data["products"] if p.get("post_author"))
print(f"Productos con post_author: {con_author} de {len(data['products'])}")