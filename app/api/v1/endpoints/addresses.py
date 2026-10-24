# ============================================================
# ENDPOINTS DE DIRECCIONES
# ============================================================
# Todas las rutas están prefijadas con /users/me/addresses.
# El usuario solo puede gestionar sus propias direcciones.

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.db.session import get_db
from app.models.address import Address
from app.schemas.address import AddressCreate, AddressRead, AddressUpdate


router = APIRouter(prefix="/users/me/addresses", tags=["addresses"])


# ============================================================
# HELPER: DESMARCAR OTRAS DIRECCIONES PREDETERMINADAS
# ============================================================

async def _unset_other_defaults(
    db: AsyncSession,
    user_id: int,
    exclude_id: int | None = None,
) -> None:
    """
    Quita is_default=False a todas las direcciones del usuario
    excepto a la que acabamos de marcar como predeterminada.
    """
    stmt = (
        update(Address)
        .where(Address.user_id == user_id)
        .where(Address.is_default.is_(True))
    )
    if exclude_id is not None:
        stmt = stmt.where(Address.id != exclude_id)
    stmt = stmt.values(is_default=False)

    await db.execute(stmt)


# ============================================================
# LISTAR DIRECCIONES
# ============================================================

@router.get(
    "",
    response_model=list[AddressRead],
    summary="Listar mis direcciones",
)
async def list_my_addresses(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[Address]:
    """Devuelve todas las direcciones del usuario autenticado."""
    result = await db.execute(
        select(Address)
        .where(Address.user_id == current_user.id)
        .where(Address.deleted_at.is_(None))
        .order_by(Address.is_default.desc(), Address.created_at.desc())
    )
    return list(result.scalars().all())


# ============================================================
# CREAR DIRECCIÓN
# ============================================================

@router.post(
    "",
    response_model=AddressRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear una dirección",
)
async def create_address(
    data: AddressCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Address:
    """Crea una dirección nueva para el usuario autenticado."""
    # Si esta dirección es la predeterminada, desmarcamos las demás.
    if data.is_default:
        await _unset_other_defaults(db, current_user.id)

    address = Address(
        user_id=current_user.id,
        **data.model_dump(),
    )

    db.add(address)
    await db.flush()
    await db.refresh(address)

    return address


# ============================================================
# OBTENER UNA DIRECCIÓN
# ============================================================

@router.get(
    "/{address_id}",
    response_model=AddressRead,
    summary="Obtener una dirección",
)
async def get_address(
    address_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Address:
    """Devuelve una dirección concreta del usuario autenticado."""
    result = await db.execute(
        select(Address)
        .where(Address.id == address_id)
        .where(Address.user_id == current_user.id)
        .where(Address.deleted_at.is_(None))
    )
    address = result.scalar_one_or_none()

    if address is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dirección no encontrada",
        )

    return address


# ============================================================
# ACTUALIZAR DIRECCIÓN
# ============================================================

@router.patch(
    "/{address_id}",
    response_model=AddressRead,
    summary="Actualizar una dirección",
)
async def update_address(
    address_id: int,
    data: AddressUpdate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Address:
    """Actualiza una dirección del usuario autenticado."""
    # Buscar la dirección.
    result = await db.execute(
        select(Address)
        .where(Address.id == address_id)
        .where(Address.user_id == current_user.id)
        .where(Address.deleted_at.is_(None))
    )
    address = result.scalar_one_or_none()

    if address is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dirección no encontrada",
        )

    # Si se marca como predeterminada, desmarcamos las demás.
    if data.is_default is True:
        await _unset_other_defaults(db, current_user.id, exclude_id=address.id)

    # Aplicar solo los campos enviados (partial update).
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(address, field, value)

    await db.flush()
    await db.refresh(address)

    return address


# ============================================================
# ELIMINAR DIRECCIÓN (SOFT DELETE)
# ============================================================

@router.delete(
    "/{address_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar una dirección",
)
async def delete_address(
    address_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Elimina (soft delete) una dirección del usuario autenticado."""
    from datetime import datetime, timezone

    result = await db.execute(
        select(Address)
        .where(Address.id == address_id)
        .where(Address.user_id == current_user.id)
        .where(Address.deleted_at.is_(None))
    )
    address = result.scalar_one_or_none()

    if address is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dirección no encontrada",
        )

    # Soft delete: marcamos deleted_at en lugar de borrar la fila.
    address.deleted_at = datetime.now(timezone.utc)
    await db.flush()


# ============================================================
# MARCAR COMO PREDETERMINADA
# ============================================================

@router.post(
    "/{address_id}/default",
    response_model=AddressRead,
    summary="Marcar dirección como predeterminada",
)
async def set_default_address(
    address_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Address:
    """Marca una dirección como predeterminada y desmarca las demás."""
    result = await db.execute(
        select(Address)
        .where(Address.id == address_id)
        .where(Address.user_id == current_user.id)
        .where(Address.deleted_at.is_(None))
    )
    address = result.scalar_one_or_none()

    if address is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dirección no encontrada",
        )

    # Desmarcar las demás.
    await _unset_other_defaults(db, current_user.id, exclude_id=address.id)

    address.is_default = True
    await db.flush()
    await db.refresh(address)

    return address