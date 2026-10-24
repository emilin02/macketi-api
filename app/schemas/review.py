# ============================================================
# SCHEMAS DE RESEÑA
# ============================================================
# Pydantic schemas para request/response de reseñas.

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ============================================================
# BASE
# ============================================================

class ReviewBase(BaseModel):
    """Campos comunes a todos los schemas de reseña."""

    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=2000)


# ============================================================
# CREATE
# ============================================================

class ReviewCreate(ReviewBase):
    """Datos para crear una reseña."""
    pass


# ============================================================
# UPDATE
# ============================================================

class ReviewUpdate(BaseModel):
    """Campos actualizables de una reseña."""

    rating: int | None = Field(default=None, ge=1, le=5)
    comment: str | None = Field(default=None, max_length=2000)


# ============================================================
# READ
# ============================================================

class ReviewBuyerInfo(BaseModel):
    """Info resumida del comprador que se incluye en la reseña."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str | None = None
    avatar_url: str | None = None


class ReviewRead(ReviewBase):
    """Datos completos de la reseña."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    buyer_id: int
    product_id: int
    order_id: int | None = None
    is_verified_purchase: bool
    is_published: bool
    created_at: datetime
    updated_at: datetime
    buyer: ReviewBuyerInfo