# ============================================================
# SCHEMAS DE PRODUCTO
# ============================================================
# Pydantic schemas para request/response de productos.

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.product import ProductApprovalStatus
from app.schemas.offer import OfferReadWithStore


# ============================================================
# BASE
# ============================================================

class ProductBase(BaseModel):
    """Campos comunes a todos los schemas de producto."""

    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    short_description: str | None = Field(default=None, max_length=500)
    category_id: int | None = None
    brand_id: int | None = None


# ============================================================
# CREATE (propuesta del vendedor)
# ============================================================

class ProductCreate(ProductBase):
    """
    Datos para proponer un producto nuevo.
    El producto entra en estado PENDING hasta que el admin lo revise.
    """
    slug: str = Field(min_length=1, max_length=200, pattern=r"^[a-z0-9-]+$")


# ============================================================
# UPDATE (admin)
# ============================================================

class ProductUpdate(BaseModel):
    """Campos actualizables del producto (admin)."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    short_description: str | None = Field(default=None, max_length=500)
    category_id: int | None = None
    brand_id: int | None = None
    is_active: bool | None = None


# ============================================================
# READ
# ============================================================

class ProductRead(ProductBase):
    """Datos completos del producto (admin)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    is_active: bool
    approval_status: ProductApprovalStatus
    rejection_reason: str | None = None
    proposed_by_id: int | None = None
    reviewed_by_id: int | None = None
    reviewed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ProductReadPublic(BaseModel):
    """Vista pública del producto (sin campos internos)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    name: str
    description: str | None = None
    short_description: str | None = None
    category_id: int | None = None
    brand_id: int | None = None
    created_at: datetime


# ============================================================
# PRODUCTO CON OFERTAS (vista pública completa)
# ============================================================

class ProductWithOffers(ProductReadPublic):
    """
    Vista pública de un producto con todas sus ofertas.
    Es lo que ve el comprador en la página de producto.
    """
    offers: list[OfferReadWithStore] = []


# ============================================================
# APROBACIÓN / RECHAZO (admin)
# ============================================================

class ProductReject(BaseModel):
    """Body para rechazar un producto."""

    reason: str = Field(
        min_length=3,
        max_length=500,
        description="Motivo corto del rechazo (visible para el vendedor).",
    )