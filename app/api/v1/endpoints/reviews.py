# ============================================================
# ENDPOINTS DE RESEÑAS
# ============================================================
# - Crear reseña (solo compradores verificados).
# - Listar reseñas de un producto (público).
# - Editar mi reseña.
# - Eliminar mi reseña.
#
# Al crear/editar/borrar, se recalcula Product.rating_avg.

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.db.session import get_db
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.product import Product, ProductApprovalStatus
from app.models.review import Review
from app.models.user import UserRole
from app.schemas.review import ReviewCreate, ReviewRead, ReviewUpdate


router = APIRouter(tags=["reviews"])


# ============================================================
# HELPER: RECALCULAR RATING DEL PRODUCTO
# ============================================================

async def _recalculate_product_rating(db: AsyncSession, product_id: int) -> None:
    """
    Recalcula el rating_avg y rating_count del producto
    a partir de todas sus reseñas publicadas.
    """
    result = await db.execute(
        select(
            func.avg(Review.rating).label("avg"),
            func.count(Review.id).label("count"),
        )
        .where(Review.product_id == product_id)
        .where(Review.is_published.is_(True))
    )
    row = result.one()
    avg = float(row.avg) if row.avg is not None else 0.0
    count = int(row.count) if row.count is not None else 0

    # Actualizar el producto.
    result = await db.execute(
        select(Product).where(Product.id == product_id)
    )
    product = result.scalar_one_or_none()
    if product is not None:
        # Nota: los campos rating_avg y rating_count hay que
        # añadirlos al modelo Product. Si no existen, este bloque
        # no se ejecuta y no pasa nada.
        if hasattr(product, "rating_avg"):
            product.rating_avg = avg
        if hasattr(product, "rating_count"):
            product.rating_count = count


# ============================================================
# HELPER: VERIFICAR COMPRA
# ============================================================

async def _has_purchased(
    db: AsyncSession,
    buyer_id: int,
    product_id: int,
) -> tuple[bool, int | None]:
    """
    Verifica si el usuario ha comprado el producto.
    Devuelve (ha_comprado, order_id_de_la_compra).
    """
    result = await db.execute(
        select(OrderItem.order_id)
        .join(Order, Order.id == OrderItem.order_id)
        .join(Product, Product.id == product_id)  # solo para validar
        .where(Order.buyer_id == buyer_id)
        .where(OrderItem.offer_id.in_(
            select(OrderItem.offer_id)
            .join(Product, Product.id == product_id)
            .limit(0)
        ))
        .limit(1)
    )
    # La consulta de arriba es compleja; mejor hacerlo en dos pasos:

    # Paso 1: encontrar las ofertas del producto.
    from app.models.offer import Offer
    result = await db.execute(
        select(Offer.id).where(Offer.product_id == product_id)
    )
    offer_ids = [row[0] for row in result.all()]

    if not offer_ids:
        return False, None

    # Paso 2: buscar un pedido del comprador que incluya alguna
    # de esas ofertas.
    result = await db.execute(
        select(OrderItem.order_id)
        .join(Order, Order.id == OrderItem.order_id)
        .where(Order.buyer_id == buyer_id)
        .where(OrderItem.offer_id.in_(offer_ids))
        .limit(1)
    )
    order_id = result.scalar_one_or_none()

    return (order_id is not None), order_id


# ============================================================
# CREAR RESEÑA (comprador verificado)
# ============================================================

@router.post(
    "/products/{slug}/reviews",
    response_model=ReviewRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear una reseña de producto",
)
async def create_review(
    slug: str,
    data: ReviewCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Review:
    """
    Crea una reseña. Solo usuarios que hayan comprado el producto.
    Una reseña por producto y comprador.
    """
    # Buscar el producto.
    result = await db.execute(
        select(Product)
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

    # Verificar que no haya reseñado ya.
    result = await db.execute(
        select(Review)
        .where(Review.buyer_id == current_user.id)
        .where(Review.product_id == product.id)
    )
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya has reseñado este producto",
        )

    # Verificar compra.
    has_purchased, order_id = await _has_purchased(
        db, current_user.id, product.id
    )

    # Crear la reseña.
    review = Review(
        buyer_id=current_user.id,
        product_id=product.id,
        order_id=order_id,
        rating=data.rating,
        comment=data.comment,
        is_verified_purchase=has_purchased,
    )
    db.add(review)
    await db.flush()

    # Recalcular rating del producto.
    await _recalculate_product_rating(db, product.id)

    # Recargar con la relación buyer.
    result = await db.execute(
        select(Review)
        .options(selectinload(Review.buyer))
        .where(Review.id == review.id)
    )
    return result.scalar_one()


# ============================================================
# LISTAR RESEÑAS DE UN PRODUCTO (público)
# ============================================================

@router.get(
    "/products/{slug}/reviews",
    response_model=list[ReviewRead],
    summary="Listar reseñas de un producto",
)
async def list_product_reviews(
    slug: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = 20,
    offset: int = 0,
) -> list[Review]:
    """
    Lista las reseñas publicadas de un producto.
    Ordenadas por más recientes primero.
    """
    # Buscar el producto.
    result = await db.execute(
        select(Product).where(Product.slug == slug)
    )
    product = result.scalar_one_or_none()

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado",
        )

    # Listar reseñas.
    result = await db.execute(
        select(Review)
        .options(selectinload(Review.buyer))
        .where(Review.product_id == product.id)
        .where(Review.is_published.is_(True))
        .order_by(Review.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


# ============================================================
# ACTUALIZAR MI RESEÑA
# ============================================================

@router.patch(
    "/reviews/{review_id}",
    response_model=ReviewRead,
    summary="Actualizar mi reseña",
)
async def update_review(
    review_id: int,
    data: ReviewUpdate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Review:
    """Actualiza una reseña propia."""
    result = await db.execute(
        select(Review)
        .options(selectinload(Review.buyer))
        .where(Review.id == review_id)
    )
    review = result.scalar_one_or_none()

    if review is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reseña no encontrada",
        )

    # Solo el autor o un admin pueden editarla.
    is_admin = UserRole.ADMIN in current_user.roles
    if review.buyer_id != current_user.id and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para editar esta reseña",
        )

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(review, field, value)

    await db.flush()

    # Recalcular rating del producto.
    await _recalculate_product_rating(db, review.product_id)

    await db.refresh(review)
    return review


# ============================================================
# ELIMINAR MI RESEÑA
# ============================================================

@router.delete(
    "/reviews/{review_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar mi reseña",
)
async def delete_review(
    review_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Elimina una reseña propia (o de cualquier usuario si es admin)."""
    result = await db.execute(
        select(Review).where(Review.id == review_id)
    )
    review = result.scalar_one_or_none()

    if review is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reseña no encontrada",
        )

    is_admin = UserRole.ADMIN in current_user.roles
    if review.buyer_id != current_user.id and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para eliminar esta reseña",
        )

    product_id = review.product_id
    await db.delete(review)
    await db.flush()

    # Recalcular rating del producto.
    await _recalculate_product_rating(db, product_id)