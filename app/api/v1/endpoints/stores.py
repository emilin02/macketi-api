# ============================================================
# ENDPOINTS DE TIENDAS
# ============================================================

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentAdmin, CurrentUser
from app.db.session import get_db
from app.models.store import Store, StoreVertical
from app.models.user import UserRole
from app.schemas.store import (
    StoreCreate,
    StoreRead,
    StoreReadPublic,
    StoreUpdate,
)


router = APIRouter(prefix="/stores", tags=["stores"])


# ============================================================
# HELPER: VERIFICAR PROPIEDAD
# ============================================================

def _ensure_owner(store: Store, user_id: int, is_admin: bool = False) -> None:
    """Verifica que el usuario es dueño de la tienda (o admin)."""
    if store.owner_id != user_id and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para modificar esta tienda",
        )


# ============================================================
# LISTAR TIENDAS (público)
# ============================================================

@router.get(
    "",
    response_model=list[StoreReadPublic],
    summary="Listar tiendas verificadas",
)
async def list_stores(
    db: Annotated[AsyncSession, Depends(get_db)],
    vertical: StoreVertical | None = None,
    city: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Store]:
    """
    Devuelve las tiendas verificadas y activas.
    Solo muestra tiendas con is_verified=True y is_active=True.
    """
    stmt = (
        select(Store)
        .where(Store.is_active.is_(True))
        .where(Store.is_verified.is_(True))
        .where(Store.deleted_at.is_(None))
        .order_by(Store.rating_avg.desc(), Store.total_orders.desc())
        .limit(limit)
        .offset(offset)
    )

    if vertical:
        stmt = stmt.where(Store.vertical == vertical)
    if city:
        stmt = stmt.where(Store.city == city)

    result = await db.execute(stmt)
    return list(result.scalars().all())


# ============================================================
# MIS TIENDAS (vendedor)
# ============================================================

@router.get(
    "/me",
    response_model=list[StoreRead],
    summary="Listar mis tiendas",
)
async def list_my_stores(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[Store]:
    """Devuelve todas las tiendas del usuario autenticado."""
    result = await db.execute(
        select(Store)
        .where(Store.owner_id == current_user.id)
        .where(Store.deleted_at.is_(None))
        .order_by(Store.created_at.desc())
    )
    return list(result.scalars().all())


# ============================================================
# OBTENER UNA TIENDA POR SLUG (público)
# ============================================================

@router.get(
    "/{slug}",
    response_model=StoreReadPublic,
    summary="Obtener una tienda por slug",
)
async def get_store(
    slug: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Store:
    """Devuelve una tienda por su slug."""
    result = await db.execute(
        select(Store)
        .where(Store.slug == slug)
        .where(Store.deleted_at.is_(None))
    )
    store = result.scalar_one_or_none()

    if store is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tienda no encontrada",
        )

    return store


# ============================================================
# CREAR TIENDA (usuario logueado)
# ============================================================

@router.post(
    "",
    response_model=StoreRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear una tienda",
)
async def create_store(
    data: StoreCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Store:
    """
    Crea una tienda. Cualquier usuario logueado puede crear una.
    Al crearla, se añade automáticamente el rol 'vendor' al usuario.
    La tienda queda pendiente de verificación por el admin.
    """
    # Verificar que el slug no exista.
    result = await db.execute(
        select(Store).where(Store.slug == data.slug)
    )
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una tienda con ese slug",
        )

    # Crear la tienda.
    store = Store(
        owner_id=current_user.id,
        **data.model_dump(),
        is_verified=False,  # pendiente de verificación por admin
    )
    db.add(store)

    # Añadir el rol 'vendor' al usuario si no lo tiene.
    if UserRole.VENDOR not in current_user.roles:
        current_user.roles = [*current_user.roles, UserRole.VENDOR]

    await db.flush()
    await db.refresh(store)

    return store


# ============================================================
# ACTUALIZAR TIENDA (dueño o admin)
# ============================================================

@router.patch(
    "/{store_id}",
    response_model=StoreRead,
    summary="Actualizar una tienda",
)
async def update_store(
    store_id: int,
    data: StoreUpdate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Store:
    """Actualiza una tienda. Solo el dueño o un admin."""
    result = await db.execute(
        select(Store)
        .where(Store.id == store_id)
        .where(Store.deleted_at.is_(None))
    )
    store = result.scalar_one_or_none()

    if store is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tienda no encontrada",
        )

    # Verificar propiedad.
    _ensure_owner(
        store,
        current_user.id,
        is_admin=UserRole.ADMIN in current_user.roles,
    )

    # Aplicar solo los campos enviados.
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(store, field, value)

    await db.flush()
    await db.refresh(store)

    return store


# ============================================================
# DESACTIVAR TIENDA (dueño o admin)
# ============================================================

@router.delete(
    "/{store_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Desactivar una tienda",
)
async def delete_store(
    store_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Desactiva una tienda (soft delete). Solo el dueño o un admin."""
    result = await db.execute(
        select(Store)
        .where(Store.id == store_id)
        .where(Store.deleted_at.is_(None))
    )
    store = result.scalar_one_or_none()

    if store is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tienda no encontrada",
        )

    _ensure_owner(
        store,
        current_user.id,
        is_admin=UserRole.ADMIN in current_user.roles,
    )

    from datetime import datetime, timezone
    store.deleted_at = datetime.now(timezone.utc)
    store.is_active = False
    await db.flush()


# ============================================================
# VERIFICAR TIENDA (admin)
# ============================================================

@router.post(
    "/{store_id}/verify",
    response_model=StoreRead,
    summary="Verificar una tienda (admin)",
)
async def verify_store(
    store_id: int,
    current_admin: CurrentAdmin,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Store:
    """Marca una tienda como verificada. Solo admin."""
    result = await db.execute(
        select(Store)
        .where(Store.id == store_id)
        .where(Store.deleted_at.is_(None))
    )
    store = result.scalar_one_or_none()

    if store is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tienda no encontrada",
        )

    store.is_verified = True
    await db.flush()
    await db.refresh(store)

    return store


# ============================================================
# DESVERIFICAR TIENDA (admin)
# ============================================================

@router.post(
    "/{store_id}/unverify",
    response_model=StoreRead,
    summary="Desverificar una tienda (admin)",
)
async def unverify_store(
    store_id: int,
    current_admin: CurrentAdmin,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Store:
    """Desmarca la verificación de una tienda. Solo admin."""
    result = await db.execute(
        select(Store)
        .where(Store.id == store_id)
        .where(Store.deleted_at.is_(None))
    )
    store = result.scalar_one_or_none()

    if store is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tienda no encontrada",
        )

    store.is_verified = False
    await db.flush()
    await db.refresh(store)

    return store