# ============================================================
# ENDPOINTS DE MARCAS
# ============================================================
# Público: listar y ver marcas.
# Admin: crear, actualizar y desactivar.

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentAdmin
from app.db.session import get_db
from app.models.brand import Brand
from app.schemas.brand import BrandCreate, BrandRead, BrandUpdate


router = APIRouter(prefix="/brands", tags=["brands"])


# ============================================================
# LISTAR MARCAS (público)
# ============================================================

@router.get(
    "",
    response_model=list[BrandRead],
    summary="Listar marcas activas",
)
async def list_brands(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[Brand]:
    """Devuelve todas las marcas activas."""
    result = await db.execute(
        select(Brand)
        .where(Brand.is_active.is_(True))
        .order_by(Brand.name)
    )
    return list(result.scalars().all())


# ============================================================
# OBTENER MARCA POR SLUG (público)
# ============================================================

@router.get(
    "/{slug}",
    response_model=BrandRead,
    summary="Obtener una marca por slug",
)
async def get_brand(
    slug: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Brand:
    """Devuelve una marca por su slug."""
    result = await db.execute(
        select(Brand).where(Brand.slug == slug)
    )
    brand = result.scalar_one_or_none()

    if brand is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Marca no encontrada",
        )

    return brand


# ============================================================
# CREAR MARCA (admin)
# ============================================================

@router.post(
    "",
    response_model=BrandRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear una marca (admin)",
)
async def create_brand(
    data: BrandCreate,
    current_admin: CurrentAdmin,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Brand:
    """Crea una marca. Solo admin."""
    result = await db.execute(
        select(Brand).where(Brand.slug == data.slug)
    )
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una marca con ese slug",
        )

    brand = Brand(**data.model_dump())
    db.add(brand)
    await db.flush()
    await db.refresh(brand)

    return brand


# ============================================================
# ACTUALIZAR MARCA (admin)
# ============================================================

@router.patch(
    "/{brand_id}",
    response_model=BrandRead,
    summary="Actualizar una marca (admin)",
)
async def update_brand(
    brand_id: int,
    data: BrandUpdate,
    current_admin: CurrentAdmin,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Brand:
    """Actualiza una marca. Solo admin."""
    result = await db.execute(
        select(Brand).where(Brand.id == brand_id)
    )
    brand = result.scalar_one_or_none()

    if brand is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Marca no encontrada",
        )

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(brand, field, value)

    await db.flush()
    await db.refresh(brand)

    return brand


# ============================================================
# DESACTIVAR MARCA (admin, soft delete)
# ============================================================

@router.delete(
    "/{brand_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Desactivar una marca (admin)",
)
async def delete_brand(
    brand_id: int,
    current_admin: CurrentAdmin,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Desactiva una marca. Solo admin."""
    result = await db.execute(
        select(Brand).where(Brand.id == brand_id)
    )
    brand = result.scalar_one_or_none()

    if brand is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Marca no encontrada",
        )

    brand.is_active = False
    await db.flush()