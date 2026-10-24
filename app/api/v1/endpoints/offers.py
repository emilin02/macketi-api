# ============================================================
# ENDPOINTS DE OFERTAS (vendedor)
# ============================================================

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.db.session import get_db
from app.models.offer import Offer
from app.models.store import Store
from app.models.user import UserRole
from app.schemas.offer import OfferRead, OfferUpdate


router = APIRouter(prefix="/offers", tags=["offers"])


# ============================================================
# MIS OFERTAS
# ============================================================

@router.get(
    "/me",
    response_model=list[OfferRead],
    summary="Mis ofertas (vendedor)",
)
async def list_my_offers(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[Offer]:
    """Lista todas las ofertas de las tiendas del usuario autenticado."""
    result = await db.execute(
        select(Store.id)
        .where(Store.owner_id == current_user.id)
        .where(Store.deleted_at.is_(None))
    )
    store_ids = [row[0] for row in result.all()]

    if not store_ids:
        return []

    result = await db.execute(
        select(Offer)
        .where(Offer.store_id.in_(store_ids))
        .where(Offer.deleted_at.is_(None))
        .order_by(Offer.created_at.desc())
    )
    return list(result.scalars().all())


# ============================================================
# ACTUALIZAR OFERTA (vendedor dueño o admin)
# ============================================================

@router.patch(
    "/{offer_id}",
    response_model=OfferRead,
    summary="Actualizar una oferta",
)
async def update_offer(
    offer_id: int,
    data: OfferUpdate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Offer:
    """Actualiza una oferta. Solo el dueño o admin."""
    result = await db.execute(
        select(Offer)
        .options(selectinload(Offer.store))
        .where(Offer.id == offer_id)
        .where(Offer.deleted_at.is_(None))
    )
    offer = result.scalar_one_or_none()

    if offer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Oferta no encontrada",
        )

    is_admin = UserRole.ADMIN in current_user.roles
    if offer.store.owner_id != current_user.id and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para modificar esta oferta",
        )

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(offer, field, value)

    await db.flush()
    await db.refresh(offer)

    return offer


# ============================================================
# ELIMINAR OFERTA (soft delete)
# ============================================================

@router.delete(
    "/{offer_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar una oferta",
)
async def delete_offer(
    offer_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Elimina (soft delete) una oferta. Solo el dueño o admin."""
    result = await db.execute(
        select(Offer)
        .options(selectinload(Offer.store))
        .where(Offer.id == offer_id)
        .where(Offer.deleted_at.is_(None))
    )
    offer = result.scalar_one_or_none()

    if offer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Oferta no encontrada",
        )

    is_admin = UserRole.ADMIN in current_user.roles
    if offer.store.owner_id != current_user.id and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para eliminar esta oferta",
        )

    offer.deleted_at = datetime.now(timezone.utc)
    await db.flush()