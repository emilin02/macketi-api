# ============================================================
# SCRIPT DE CARGA A POSTGRESQL
# ============================================================
# Lee el JSON transformado y lo inserta en PostgreSQL.
#
# Es IDEMPOTENTE: si lo ejecutas dos veces, no duplica datos.
# Usa INSERT ... ON CONFLICT DO NOTHING para cada entidad.
#
# Uso:
#   python scripts/load_to_postgres.py
#
# Orden de inserción (respeta FKs):
#   1. Categorías raíz
#   2. Categorías hijas (por niveles)
#   3. Usuarios placeholder para vendedores
#   4. Tiendas
#   5. Productos
#   6. Ofertas

import asyncio
import json
import secrets
import sys
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.security import hash_password  # noqa: E402
from app.db.session import async_session_factory  # noqa: E402
from app.models.category import Category  # noqa: E402
from app.models.offer import Offer, OfferCondition, OfferStatus  # noqa: E402
from app.models.product import Product, ProductApprovalStatus  # noqa: E402
from app.models.store import Store, StoreVertical  # noqa: E402
from app.models.user import User, UserRole  # noqa: E402


# ============================================================
# RUTAS
# ============================================================

DATA_DIR = Path(__file__).parent.parent / "data"
INPUT_FILE = DATA_DIR / "macketi_products.json"


# ============================================================
# MAPEO DE VERTICALES
# ============================================================

VERTICAL_MAP = {
    "tienda": StoreVertical.TIENDA,
    "farmacia": StoreVertical.FARMACIA,
    "restaurante": StoreVertical.RESTAURANTE,
    "supermercado": StoreVertical.SUPERMERCADO,
}


def map_vertical(value: str | None) -> StoreVertical:
    """Convierte el slug de la vertical al enum de PostgreSQL."""
    if not value:
        return StoreVertical.TIENDA
    return VERTICAL_MAP.get(value.lower(), StoreVertical.TIENDA)


# ============================================================
# CARGA DE CATEGORÍAS
# ============================================================

async def load_categories(session, categories: list[dict]) -> dict[int, int]:
    """
    Inserta las categorías respetando la jerarquía.
    Devuelve un mapa {woo_id: category_id_local}.
    """
    print("📂 Insertando categorías...")

    # Ordenar por jerarquía: raíces primero
    roots = [c for c in categories if c["parent_woo_id"] is None]
    others = [c for c in categories if c["parent_woo_id"] is not None]

    # Mapa de woo_id → id local
    woo_to_local: dict[int, int] = {}

    # Insertar raíces
    for cat in roots:
        stmt = pg_insert(Category).values(
            slug=cat["slug"],
            name=cat["name"],
            description=cat.get("description"),
            image_url=cat.get("image_url"),
            parent_id=None,
            position=cat.get("position", 0),
            is_active=True,
        ).on_conflict_do_nothing(index_elements=["slug"])

        await session.execute(stmt)
        await session.flush()

        # Recuperar el ID
        result = await session.execute(
            select(Category.id).where(Category.slug == cat["slug"])
        )
        local_id = result.scalar_one()
        woo_to_local[cat["woo_id"]] = local_id

    # Insertar el resto, resolviendo parent_id
    # Como puede haber anidamiento profundo, iteramos hasta que
    # no queden categorías pendientes.
    pending = list(others)
    max_iterations = 10
    iteration = 0

    while pending and iteration < max_iterations:
        iteration += 1
        next_pending = []

        for cat in pending:
            parent_woo = cat["parent_woo_id"]
            if parent_woo not in woo_to_local:
                # Su padre aún no está insertado
                next_pending.append(cat)
                continue

            stmt = pg_insert(Category).values(
                slug=cat["slug"],
                name=cat["name"],
                description=cat.get("description"),
                image_url=cat.get("image_url"),
                parent_id=woo_to_local[parent_woo],
                position=cat.get("position", 0),
                is_active=True,
            ).on_conflict_do_nothing(index_elements=["slug"])

            await session.execute(stmt)
            await session.flush()

            result = await session.execute(
                select(Category.id).where(Category.slug == cat["slug"])
            )
            local_id = result.scalar_one()
            woo_to_local[cat["woo_id"]] = local_id

        pending = next_pending

    await session.commit()
    print(f"   {len(woo_to_local)} categorías insertadas/actualizadas")
    return woo_to_local


# ============================================================
# CARGA DE USUARIOS Y TIENDAS
# ============================================================

async def load_users_and_stores(
    session,
    stores: list[dict],
    products: list[dict],
) -> dict[int, int]:
    """
    Crea un usuario placeholder por cada tienda y luego inserta
    la tienda asociada.
    Devuelve un mapa {dokan_id: store_id_local}.
    """
    print("👤 Creando usuarios placeholder para vendedores...")

    # Contar productos por tienda para marcar las vacías
    product_count_by_store: dict[int, int] = {}
    for product in products:
        author = product.get("post_author")
        if author:
            product_count_by_store[author] = product_count_by_store.get(author, 0) + 1

    dokan_to_local: dict[int, int] = {}

    for store_data in stores:
        dokan_id = store_data["dokan_id"]

        # 1. Crear (o recuperar) el usuario placeholder
        email = f"vendor-{dokan_id}@migrated.macketi.local"

        result = await session.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()

        if user is None:
            # Crear usuario nuevo
            user = User(
                email=email,
                password_hash=hash_password(secrets.token_urlsafe(32)),
                full_name=store_data["name"],
                roles=[UserRole.VENDOR],
                is_active=True,
                email_verified=False,
            )
            session.add(user)
            await session.flush()
            print(f"   Usuario creado: {email}")

        # 2. Crear la tienda
        has_products = product_count_by_store.get(dokan_id, 0) > 0

        stmt = pg_insert(Store).values(
            owner_id=user.id,
            slug=store_data["slug"],
            name=store_data["name"],
            description=store_data.get("description"),
            logo_url=store_data.get("logo_url"),
            banner_url=store_data.get("banner_url"),
            phone=store_data.get("phone"),
            email=None,  # no lo tenemos
            vertical=map_vertical(store_data.get("vertical")),
            address=None,
            city=None,
            is_active=has_products,  # solo activa si tiene productos
            is_verified=False,
            rating_avg=store_data.get("rating_avg", 0.0),
            rating_count=store_data.get("rating_count", 0),
            total_orders=0,
            commission_pct=None,
        ).on_conflict_do_nothing(index_elements=["slug"])

        await session.execute(stmt)
        await session.flush()

        # Recuperar el ID local
        result = await session.execute(
            select(Store.id).where(Store.slug == store_data["slug"])
        )
        local_id = result.scalar_one()
        dokan_to_local[dokan_id] = local_id

    await session.commit()
    print(f"   {len(dokan_to_local)} tiendas insertadas/actualizadas")
    return dokan_to_local


# ============================================================
# CARGA DE PRODUCTOS
# ============================================================

async def load_products(
    session,
    products: list[dict],
    woo_to_local_category: dict[int, int],
) -> dict[int, int]:
    """
    Inserta los productos.
    Devuelve un mapa {woo_product_id: product_id_local}.
    """
    print("📦 Insertando productos...")

    woo_to_local: dict[int, int] = {}

    for product in products:
        # Resolver categoría
        local_category_id = None
        if product.get("category_woo_id"):
            local_category_id = woo_to_local_category.get(product["category_woo_id"])

        stmt = pg_insert(Product).values(
            slug=product["slug"],
            name=product["name"],
            description=product.get("description"),
            short_description=product.get("short_description"),
            category_id=local_category_id,
            brand_id=None,
            is_active=True,
            approval_status=ProductApprovalStatus.APPROVED,
        ).on_conflict_do_nothing(index_elements=["slug"])

        await session.execute(stmt)
        await session.flush()

        # Recuperar ID
        result = await session.execute(
            select(Product.id).where(Product.slug == product["slug"])
        )
        local_id = result.scalar_one()
        woo_to_local[product["woo_id"]] = local_id

    await session.commit()
    print(f"   {len(woo_to_local)} productos insertados/actualizados")
    return woo_to_local


# ============================================================
# CARGA DE OFERTAS
# ============================================================

async def load_offers(
    session,
    offers: list[dict],
    woo_to_local_product: dict[int, int],
    dokan_to_local_store: dict[int, int],
) -> int:
    """
    Inserta las ofertas.
    Devuelve el número de ofertas insertadas.
    """
    print("🏷️  Insertando ofertas...")

    inserted = 0
    skipped = 0

    for offer in offers:
        # Resolver producto
        local_product_id = woo_to_local_product.get(offer["product_woo_id"])
        if not local_product_id:
            skipped += 1
            continue

        # Resolver tienda
        local_store_id = dokan_to_local_store.get(offer["store_dokan_id"])
        if not local_store_id:
            skipped += 1
            continue

        # Verificar si ya existe esta oferta (mismo producto + tienda + precio)
        result = await session.execute(
            select(Offer.id)
            .where(Offer.product_id == local_product_id)
            .where(Offer.store_id == local_store_id)
        )
        if result.scalar_one_or_none() is not None:
            skipped += 1
            continue

        # Insertar
        session.add(Offer(
            product_id=local_product_id,
            store_id=local_store_id,
            price=offer["price"],
            compare_price=offer.get("compare_price"),
            stock=offer.get("stock", 0),
            stock_unlimited=offer.get("stock_unlimited", False),
            condition=OfferCondition.NEW,
            status=OfferStatus.ACTIVE if offer.get("status") == "active" else OfferStatus.OUT_OF_STOCK,
            sku=offer.get("sku"),
            requires_prescription=offer.get("requires_prescription", False),
            prep_time_min=offer.get("prep_time_min"),
        ))
        inserted += 1

    await session.commit()
    print(f"   {inserted} ofertas insertadas, {skipped} saltadas (ya existían o sin referencia)")
    return inserted


# ============================================================
# EJECUCIÓN PRINCIPAL
# ============================================================

async def main() -> None:
    print("=" * 60)
    print("CARGA DE DATOS A POSTGRESQL")
    print("=" * 60)
    print()

    if not INPUT_FILE.exists():
        print(f"❌ No se encontró {INPUT_FILE}")
        print("   Ejecuta primero: python scripts/transform_woocommerce.py")
        return

    print(f"📖 Leyendo {INPUT_FILE}...")
    data = json.loads(INPUT_FILE.read_text(encoding="utf-8"))

    categories = data["categories"]
    stores = data["stores"]
    products = data["products"]
    offers = data["offers"]

    print(f"   {len(categories)} categorías")
    print(f"   {len(stores)} tiendas")
    print(f"   {len(products)} productos")
    print(f"   {len(offers)} ofertas")
    print()

    async with async_session_factory() as session:
        # 1. Categorías
        woo_to_local_category = await load_categories(session, categories)

        # 2. Usuarios + Tiendas
        dokan_to_local_store = await load_users_and_stores(session, stores, products)

        # 3. Productos
        woo_to_local_product = await load_products(
            session, products, woo_to_local_category
        )

        # 4. Ofertas
        total_offers = await load_offers(
            session, offers, woo_to_local_product, dokan_to_local_store
        )

    print()
    print("=" * 60)
    print("✅ CARGA COMPLETADA")
    print("=" * 60)
    print(f"Categorías:  {len(woo_to_local_category)}")
    print(f"Tiendas:     {len(dokan_to_local_store)}")
    print(f"Productos:   {len(woo_to_local_product)}")
    print(f"Ofertas:     {total_offers}")
    print()


if __name__ == "__main__":
    asyncio.run(main())