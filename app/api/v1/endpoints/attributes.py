# ============================================================
# ENDPOINTS DE ATRIBUTOS
# ============================================================
# Público: listar atributos y valores.
# Admin: crear, actualizar, eliminar.

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentAdmin
from app.db.session import get_db
from app.models.attribute import Attribute
from app.models.attribute_value import AttributeValue
from app.schemas.attribute import (
    AttributeCreate,
    AttributeRead,
    AttributeReadWithValues,
    AttributeUpdate,
    AttributeValueCreate,
    AttributeValueRead,
    AttributeValueUpdate,
)


router = APIRouter(prefix="/attributes", tags=["attributes"])


# ============================================================
# LISTAR ATRIBUTOS CON VALORES (público)
# ============================================================

@router.get(
    "",
    response_model=list[AttributeReadWithValues],
    summary="Listar atributos con sus valores",
)
async def list_attributes(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[Attribute]:
    """Devuelve todos los atributos activos con sus valores."""
    result = await db.execute(
        select(Attribute)
        .options(selectinload(Attribute.values))
        .where(Attribute.is_active.is_(True))
        .order_by(Attribute.position, Attribute.name)
    )
    return list(result.scalars().all())


# ============================================================
# OBTENER UN ATRIBUTO POR SLUG (público)
# ============================================================

@router.get(
    "/{slug}",
    response_model=AttributeReadWithValues,
    summary="Obtener un atributo por slug",
)
async def get_attribute(
    slug: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Attribute:
    """Devuelve un atributo con sus valores."""
    result = await db.execute(
        select(Attribute)
        .options(selectinload(Attribute.values))
        .where(Attribute.slug == slug)
    )
    attribute = result.scalar_one_or_none()

    if attribute is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Atributo no encontrado",
        )

    return attribute


# ============================================================
# CREAR ATRIBUTO (admin)
# ============================================================

@router.post(
    "",
    response_model=AttributeReadWithValues,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un atributo (admin)",
)
async def create_attribute(
    data: AttributeCreate,
    current_admin: CurrentAdmin,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Attribute:
    """
    Crea un atributo nuevo.
    Puede incluir valores iniciales en `values`.
    """
    # Verificar slug único.
    result = await db.execute(
        select(Attribute).where(Attribute.slug == data.slug)
    )
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un atributo con ese slug",
        )

    # Crear el atributo.
    attribute = Attribute(
        slug=data.slug,
        name=data.name,
        position=data.position,
        is_active=data.is_active,
    )
    db.add(attribute)
    await db.flush()

    # Crear valores iniciales.
    for value_data in data.values:
        value = AttributeValue(
            attribute_id=attribute.id,
            slug=value_data.slug,
            value=value_data.value,
            position=value_data.position,
        )
        db.add(value)

    await db.flush()

    # Recargar con los valores.
    result = await db.execute(
        select(Attribute)
        .options(selectinload(Attribute.values))
        .where(Attribute.id == attribute.id)
    )
    return result.scalar_one()


# ============================================================
# ACTUALIZAR ATRIBUTO (admin)
# ============================================================

@router.patch(
    "/{attribute_id}",
    response_model=AttributeRead,
    summary="Actualizar un atributo (admin)",
)
async def update_attribute(
    attribute_id: int,
    data: AttributeUpdate,
    current_admin: CurrentAdmin,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Attribute:
    """Actualiza un atributo. Solo admin."""
    result = await db.execute(
        select(Attribute).where(Attribute.id == attribute_id)
    )
    attribute = result.scalar_one_or_none()

    if attribute is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Atributo no encontrado",
        )

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(attribute, field, value)

    await db.flush()
    await db.refresh(attribute)

    return attribute


# ============================================================
# DESACTIVAR ATRIBUTO (admin)
# ============================================================

@router.delete(
    "/{attribute_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Desactivar un atributo (admin)",
)
async def delete_attribute(
    attribute_id: int,
    current_admin: CurrentAdmin,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Desactiva un atributo. Solo admin."""
    result = await db.execute(
        select(Attribute).where(Attribute.id == attribute_id)
    )
    attribute = result.scalar_one_or_none()

    if attribute is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Atributo no encontrado",
        )

    attribute.is_active = False
    await db.flush()


# ============================================================
# AÑADIR VALOR A UN ATRIBUTO (admin)
# ============================================================

@router.post(
    "/{attribute_id}/values",
    response_model=AttributeValueRead,
    status_code=status.HTTP_201_CREATED,
    summary="Añadir un valor a un atributo (admin)",
)
async def create_attribute_value(
    attribute_id: int,
    data: AttributeValueCreate,
    current_admin: CurrentAdmin,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AttributeValue:
    """Añade un valor a un atributo existente."""
    result = await db.execute(
        select(Attribute).where(Attribute.id == attribute_id)
    )
    attribute = result.scalar_one_or_none()

    if attribute is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Atributo no encontrado",
        )

    # Verificar slug único dentro del atributo.
    result = await db.execute(
        select(AttributeValue)
        .where(AttributeValue.attribute_id == attribute_id)
        .where(AttributeValue.slug == data.slug)
    )
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un valor con ese slug en este atributo",
        )

    value = AttributeValue(
        attribute_id=attribute_id,
        **data.model_dump(),
    )
    db.add(value)
    await db.flush()
    await db.refresh(value)

    return value


# ============================================================
# ACTUALIZAR VALOR DE ATRIBUTO (admin)
# ============================================================

@router.patch(
    "/values/{value_id}",
    response_model=AttributeValueRead,
    summary="Actualizar un valor de atributo (admin)",
)
async def update_attribute_value(
    value_id: int,
    data: AttributeValueUpdate,
    current_admin: CurrentAdmin,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AttributeValue:
    """Actualiza un valor de atributo."""
    result = await db.execute(
        select(AttributeValue).where(AttributeValue.id == value_id)
    )
    value = result.scalar_one_or_none()

    if value is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Valor de atributo no encontrado",
        )

    update_data = data.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        setattr(value, field, val)

    await db.flush()
    await db.refresh(value)

    return value


# ============================================================
# ELIMINAR VALOR DE ATRIBUTO (admin)
# ============================================================

@router.delete(
    "/values/{value_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar un valor de atributo (admin)",
)
async def delete_attribute_value(
    value_id: int,
    current_admin: CurrentAdmin,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """
    Elimina un valor de atributo.
    Se elimina de product_attribute_values (CASCADE).
    """
    result = await db.execute(
        select(AttributeValue).where(AttributeValue.id == value_id)
    )
    value = result.scalar_one_or_none()

    if value is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Valor de atributo no encontrado",
        )

    await db.delete(value)
    await db.flush()