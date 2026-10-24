# ============================================================
# ENDPOINTS DE ADMIN PARA PRODUCTOS
# ============================================================

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentAdmin
from app.db.session import get_db
from app.models.product import Product, ProductApprovalStatus
from app.schemas.product import ProductRead, ProductReject


router = APIRouter(prefix="/admin/products", tags=["admin-products"])


# ============================================================
# LISTAR PRODUCTOS PENDIENTES
# ============================================================

@router.get(
    "/pending",
    response_model=list[ProductRead],
    summary="Listar productos pendientes de aprobación",
)
async def list_pending_products(
    current_admin: CurrentAdmin,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[Product]:
    """Lista todos los productos en estado PENDING."""
    result = await db.execute(
        select(Product)
        .where(Product.approval_status == ProductApprovalStatus.PENDING)
        .order_by(Product.created_at.asc())
    )
    return list(result.scalars().all())


# ============================================================
# LISTAR PRODUCTOS RECHAZADOS
# ============================================================

@router.get(
    "/rejected",
    response_model=list[ProductRead],
    summary="Listar productos rechazados",
)
async def list_rejected_products(
    current_admin: CurrentAdmin,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[Product]:
    """Lista todos los productos en estado REJECTED."""
    result = await db.execute(
        select(Product)
        .where(Product.approval_status == ProductApprovalStatus.REJECTED)
        .order_by(Product.reviewed_at.desc())
    )
    return list(result.scalars().all())


# ============================================================
# APROBAR PRODUCTO
# ============================================================

@router.post(
    "/{product_id}/approve",
    response_model=ProductRead,
    summary="Aprobar un producto",
)
async def approve_product(
    product_id: int,
    current_admin: CurrentAdmin,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Product:
    """Aprueba un producto. Pasa a APPROVED y aparece en el catálogo."""
    result = await db.execute(
        select(Product).where(Product.id == product_id)
    )
    product = result.scalar_one_or_none()

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado",
        )

    product.approval_status = ProductApprovalStatus.APPROVED
    product.rejection_reason = None
    product.reviewed_by_id = current_admin.id
    product.reviewed_at = datetime.now(timezone.utc)

    await db.flush()
    await db.refresh(product)

    return product


# ============================================================
# RECHAZAR PRODUCTO
# ============================================================

@router.post(
    "/{product_id}/reject",
    response_model=ProductRead,
    summary="Rechazar un producto con motivo",
)
async def reject_product(
    product_id: int,
    data: ProductReject,
    current_admin: CurrentAdmin,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Product:
    """
    Rechaza un producto con un motivo. El vendedor verá el motivo
    y podrá editar el producto y reenviarlo.
    """
    result = await db.execute(
        select(Product).where(Product.id == product_id)
    )
    product = result.scalar_one_or_none()

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado",
        )

    product.approval_status = ProductApprovalStatus.REJECTED
    product.rejection_reason = data.reason
    product.reviewed_by_id = current_admin.id
    product.reviewed_at = datetime.now(timezone.utc)

    await db.flush()
    await db.refresh(product)

    return product