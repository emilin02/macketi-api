# ============================================================
# ENDPOINTS DE FAVORITOS
# ============================================================
# Los favoritos son privados del usuario autenticado.

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.db.session import get_db
from app.models.favorite import Favorite
from app.models.product import Product, ProductApprovalStatus
from app.schemas.favorite import FavoriteRead


router = APIRouter(tags=["favorites"])


# ============================================================
# HELPER: BUSCAR PRODUCTO POR SLUG
# ============================================================

async def _get_product_by_slug(db: AsyncSession, slug: str) -> Product:
    """Busca un producto aprobado y activo por su slug."""
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

    return product


# ============================================================
# AÑADIR A FAVORITOS
# ============================================================

@router.post(
    "/products/{slug}/favorite",
    response_model=FavoriteRead,
    status_code=status.HTTP_201_CREATED,
    summary="Añadir producto a favoritos",
)
async def add_favorite(
    slug: str,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Favorite:
    """Añade un producto a los favoritos del usuario."""
    product = await _get_product_by_slug(db, slug)

    # Verificar que no esté ya en favoritos.
    result = await db.execute(
        select(Favorite)
        .where(Favorite.user_id == current_user.id)
        .where(Favorite.product_id == product.id)
    )
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El producto ya está en tus favoritos",
        )

    favorite = Favorite(
        user_id=current_user.id,
        product_id=product.id,
    )
    db.add(favorite)
    await db.flush()
    await db.refresh(favorite)

    return favorite


# ============================================================
# QUITAR DE FAVORITOS
# ============================================================

@router.delete(
    "/products/{slug}/favorite",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Quitar producto de favoritos",
)
async def remove_favorite(
    slug: str,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Quita un producto de los favoritos del usuario."""
    product = await _get_product_by_slug(db, slug)

    result = await db.execute(
        select(Favorite)
        .where(Favorite.user_id == current_user.id)
        .where(Favorite.product_id == product.id)
    )
    favorite = result.scalar_one_or_none()

    if favorite is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El producto no está en tus favoritos",
        )

    await db.delete(favorite)
    await db.flush()


# ============================================================
# COMPROBAR SI UN PRODUCTO ESTÁ EN FAVORITOS
# ============================================================

@router.get(
    "/products/{slug}/favorite",
    response_model=dict,
    summary="Comprobar si un producto está en favoritos",
)
async def check_favorite(
    slug: str,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Devuelve si el producto está en los favoritos del usuario."""
    product = await _get_product_by_slug(db, slug)

    result = await db.execute(
        select(Favorite)
        .where(Favorite.user_id == current_user.id)
        .where(Favorite.product_id == product.id)
    )
    is_favorite = result.scalar_one_or_none() is not None

    return {"is_favorite": is_favorite}


# ============================================================
# MIS FAVORITOS
# ============================================================

@router.get(
    "/favorites/me",
    response_model=list[FavoriteRead],
    summary="Mis favoritos",
)
async def list_my_favorites(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = 50,
    offset: int = 0,
) -> list[Favorite]:
    """Lista los productos favoritos del usuario autenticado."""
    result = await db.execute(
        select(Favorite)
        .where(Favorite.user_id == current_user.id)
        .order_by(Favorite.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())