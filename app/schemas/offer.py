# ============================================================
# SCHEMAS DE OFERTA
# ============================================================
# Pydantic schemas para request/response de ofertas.

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.offer import OfferCondition, OfferStatus


# ============================================================
# BASE
# ============================================================

class OfferBase(BaseModel):
    """Campos comunes a todos los schemas de oferta."""

    price: float = Field(gt=0)
    compare_price: float | None = Field(default=None, gt=0)
    stock: int = Field(default=0, ge=0)
    stock_unlimited: bool = False
    condition: OfferCondition = OfferCondition.NEW
    status: OfferStatus = OfferStatus.ACTIVE
    sku: str | None = Field(default=None, max_length=80)
    barcode: str | None = Field(default=None, max_length=80)
    requires_prescription: bool = False
    prep_time_min: int | None = Field(default=None, ge=0)


# ============================================================
# CREATE
# ============================================================

class OfferCreate(OfferBase):
    """Datos para crear una oferta."""
    pass


# ============================================================
# UPDATE
# ============================================================

class OfferUpdate(BaseModel):
    """Campos actualizables de una oferta (todos opcionales)."""

    price: float | None = Field(default=None, gt=0)
    compare_price: float | None = Field(default=None, gt=0)
    stock: int | None = Field(default=None, ge=0)
    stock_unlimited: bool | None = None
    condition: OfferCondition | None = None
    status: OfferStatus | None = None
    sku: str | None = Field(default=None, max_length=80)
    barcode: str | None = Field(default=None, max_length=80)
    requires_prescription: bool | None = None
    prep_time_min: int | None = Field(default=None, ge=0)


# ============================================================
# READ
# ============================================================

class OfferStoreInfo(BaseModel):
    """Info resumida de la tienda que se incluye en la oferta."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    name: str
    logo_url: str | None = None
    rating_avg: float
    rating_count: int
    is_verified: bool


class OfferRead(OfferBase):
    """Datos completos de la oferta."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    store_id: int
    created_at: datetime
    updated_at: datetime


class OfferReadWithStore(OfferRead):
    """Oferta con info de la tienda (para la página de producto)."""

    store: OfferStoreInfo