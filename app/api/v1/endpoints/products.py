# ============================================================
# ENDPOINTS DE PRODUCTOS
# ============================================================
# Catálogo público con búsqueda y filtros.
#
# Para ordenar/filtrar por precio, se hace un JOIN con la
# tabla offers y se agrupa por producto, usando MIN(price).
# Esto es más rápido y más predecible que un subquery
# correlacionado.

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentAdmin, CurrentUser
from app.db.session import get_db
from app.models.category import Category
from app.models.offer import Offer, OfferStatus
from app.models.product import Product, ProductApprovalStatus
from app.models.store import Store
from app.schemas.offer import OfferCreate, OfferRead
from app.schemas.product import (
    ProductCreate,
    ProductRead,
    ProductReadPublic,
    ProductUpdate,
    ProductWithOffers,
)


router = APIRouter(prefix="/products", tags=["products"])


# ============================================================
# LISTAR PRODUCTOS (público)
# ============================================================

@router.get(
    "",
    response_model=list[ProductReadPublic],
    summary="Listar productos con filtros y ordenación",
)
async def list_products(
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    # Búsqueda
    q: str | None = Query(None, description="Buscar por nombre o descripción"),
    # Filtros
    category_id: int | None = None,
    brand_id: int | None = None,
    store_id: int | None = None,
    min_price: float | None = Query(None, ge=0),
    max_price: float | None = Query(None, ge=0),
    rating_min: float | None = Query(None, ge=0, le=5),
    in_stock: bool = Query(False),
    # Ordenación
    order_by: str = Query(
        "newest",
        pattern="^(newest|price_asc|price_desc|rating|popularity)$",
    ),
    # Paginación
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> list[Product]:
    """
    Lista productos aprobados y activos.

    Para ordenar por precio se usa el precio mínimo de las
    ofertas activas de cada producto.
    """
    # ----------------------------------------------------------
    # Query base
    # ----------------------------------------------------------
    stmt = (
        select(Product)
        .where(Product.is_active.is_(True))
        .where(Product.approval_status == ProductApprovalStatus.APPROVED)
    )

    # ----------------------------------------------------------
    # Búsqueda por texto
    # ----------------------------------------------------------
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            (Product.name.ilike(like)) | (Product.description.ilike(like))
        )

    # ----------------------------------------------------------
    # Filtros simples
    # ----------------------------------------------------------
    if category_id:
        stmt = stmt.where(Product.category_id == category_id)

    if brand_id:
        stmt = stmt.where(Product.brand_id == brand_id)

    if rating_min is not None:
        stmt = stmt.where(Product.rating_avg >= rating_min)

    # ----------------------------------------------------------
    # Filtros que requieren JOIN con offers
    # ----------------------------------------------------------
    # Subquery de ofertas activas con stock.
    active_offers = (
        select(Offer.product_id)
        .where(Offer.status == OfferStatus.ACTIVE)
        .where(Offer.deleted_at.is_(None))
    )

    if in_stock:
        stmt = stmt.where(
            Product.id.in_(
                active_offers.where(
                    (Offer.stock_unlimited.is_(True)) | (Offer.stock > 0)
                )
            )
        )

    if store_id is not None:
        stmt = stmt.where(
            Product.id.in_(
                active_offers.where(Offer.store_id == store_id)
            )
        )

    # Rango de precio: usamos EXISTS con subquery.
    if min_price is not None:
        stmt = stmt.where(
            Product.id.in_(
                active_offers.where(Offer.price >= min_price)
            )
        )

    if max_price is not None:
        stmt = stmt.where(
            Product.id.in_(
                active_offers.where(Offer.price <= max_price)
            )
        )

    # ----------------------------------------------------------
    # Contar total (sin paginación)
    # ----------------------------------------------------------
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0
    response.headers["X-Total-Count"] = str(total)

    # ----------------------------------------------------------
    # Ordenación
    # ----------------------------------------------------------
    if order_by == "newest":
        stmt = stmt.order_by(Product.created_at.desc())

    elif order_by == "rating":
        stmt = stmt.order_by(
            Product.rating_avg.desc(),
            Product.rating_count.desc(),
        )

    elif order_by == "popularity":
        stmt = stmt.order_by(Product.rating_count.desc())

    elif order_by in ("price_asc", "price_desc"):
        # Para ordenar por precio, hacemos un LEFT JOIN con offers
        # y agrupamos por producto, usando MIN(price).
        #
        # Nota: usamos una subquery para el precio mínimo y luego
        # ordenamos por ella. Evitamos GROUP BY en la query principal
        # para no complicar el SELECT de Product.
        min_price_subq = (
            select(
                Offer.product_id,
                func.min(Offer.price).label("min_price"),
            )
            .where(Offer.status == OfferStatus.ACTIVE)
            .where(Offer.deleted_at.is_(None))
            .group_by(Offer.product_id)
            .subquery()
        )

        stmt = stmt.outerjoin(
            min_price_subq,
            min_price_subq.c.product_id == Product.id,
        )

        if order_by == "price_asc":
            stmt = stmt.order_by(min_price_subq.c.min_price.asc().nullslast())
        else:
            stmt = stmt.order_by(min_price_subq.c.min_price.desc().nullslast())

    # ----------------------------------------------------------
    # Paginación
    # ----------------------------------------------------------
    stmt = stmt.limit(limit).offset(offset)

    result = await db.execute(stmt)
    return list(result.scalars().all())


# ============================================================
# OBTENER PRODUCTO CON OFERTAS (público)
# ============================================================

@router.get(
    "/{slug}",
    response_model=ProductWithOffers,
    summary="Obtener producto con sus ofertas",
)
async def get_product(
    slug: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Product:
    """Devuelve un producto con todas sus ofertas activas."""
    result = await db.execute(
        select(Product)
        .options(
            selectinload(Product.offers).selectinload(Offer.store)
        )
        .where(Product.slug == slug)
        .where(Product.is_active.is_(True))
        .where(Product.approval_status == ProductApprovalStatus.APPROVED)
    )
    product = result.scalar_one_or_none()

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado",
        )


# ============================================================
# CREAR PRODUCTO (vendedor propone, admin aprueba)
# ============================================================

@router.post(
    "",
    response_model=ProductRead,
    status_code=status.HTTP_201_CREATED,
    summary="Proponer un producto nuevo",
)
async def create_product(
    data: ProductCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Product:
    """Propone un producto nuevo. Entra en estado PENDING."""
    result = await db.execute(
        select(Product).where(Product.slug == data.slug)
    )
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un producto con ese slug",
        )

    if data.category_id is not None:
        result = await db.execute(
            select(Category).where(Category.id == data.category_id)
        )
        if result.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La categoría no existe",
            )

    product = Product(
        **data.model_dump(),
        proposed_by_id=current_user.id,
        approval_status=ProductApprovalStatus.PENDING,
    )
    db.add(product)
    await db.flush()
    await db.refresh(product)

    return product


# ============================================================
# ACTUALIZAR PRODUCTO (admin)
# ============================================================

@router.patch(
    "/{product_id}",
    response_model=ProductRead,
    summary="Actualizar un producto (admin)",
)
async def update_product(
    product_id: int,
    data: ProductUpdate,
    current_admin: CurrentAdmin,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Product:
    """Actualiza un producto. Solo admin."""
    result = await db.execute(
        select(Product).where(Product.id == product_id)
    )
    product = result.scalar_one_or_none()

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado",
        )

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product, field, value)

    await db.flush()
    await db.refresh(product)

    return product


# ============================================================
# AÑADIR OFERTA A UN PRODUCTO (vendedor)
# ============================================================

@router.post(
    "/{product_id}/offers",
    response_model=OfferRead,
    status_code=status.HTTP_201_CREATED,
    summary="Añadir una oferta a un producto",
)
async def create_offer(
    product_id: int,
    data: OfferCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Offer:
    """Añade una oferta a un producto existente."""
    result = await db.execute(
        select(Product)
        .where(Product.id == product_id)
        .where(Product.approval_status == ProductApprovalStatus.APPROVED)
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado o no aprobado",
        )

    result = await db.execute(
        select(Store)
        .where(Store.owner_id == current_user.id)
        .where(Store.is_active.is_(True))
        .where(Store.deleted_at.is_(None))
        .limit(1)
    )
    store = result.scalar_one_or_none()

    if store is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Necesitas tener al menos una tienda activa para ofertar",
        )

    offer = Offer(
        product_id=product_id,
        store_id=store.id,
        **data.model_dump(),
    )
    db.add(offer)
    await db.flush()
    await db.refresh(offer)

    return offer

# ============================================================
# ASIGNAR ATRIBUTOS A UN PRODUCTO (vendedor/admin)
# ============================================================

from app.models.attribute_value import AttributeValue
from app.schemas.attribute import ProductAttributesUpdate


@router.put(
    "/{product_id}/attributes",
    response_model=ProductRead,
    summary="Reemplazar los atributos de un producto",
)
async def set_product_attributes(
    product_id: int,
    data: ProductAttributesUpdate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Product:
    """
    Reemplaza los valores de atributo de un producto.
    Solo el dueño de una tienda que oferta ese producto o admin.
    """
    result = await db.execute(
        select(Product)
        .options(selectinload(Product.attribute_values))
        .where(Product.id == product_id)
    )
    product = result.scalar_one_or_none()

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado",
        )

    # Verificar que los valores existen.
    if data.value_ids:
        result = await db.execute(
            select(AttributeValue).where(AttributeValue.id.in_(data.value_ids))
        )
        values = list(result.scalars().all())

        if len(values) != len(set(data.value_ids)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Alguno de los valores de atributo no existe",
            )

        product.attribute_values = values
    else:
        product.attribute_values = []

    await db.flush()
    await db.refresh(product)

    return product