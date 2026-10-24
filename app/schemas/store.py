# ============================================================
# SCHEMAS DE TIENDA
# ============================================================

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.store import StoreVertical


# ============================================================
# BASE
# ============================================================

class StoreBase(BaseModel):
    """Campos comunes a todos los schemas de tienda."""

    name: str = Field(min_length=1, max_length=150)
    description: str | None = None
    logo_url: str | None = Field(default=None, max_length=500)
    banner_url: str | None = Field(default=None, max_length=500)
    phone: str | None = Field(default=None, max_length=30)
    email: EmailStr | None = None
    vertical: StoreVertical = StoreVertical.TIENDA
    address: str | None = None
    city: str | None = Field(default=None, max_length=100)


# ============================================================
# CREATE
# ============================================================

class StoreCreate(StoreBase):
    """Datos para crear una tienda."""
    slug: str = Field(min_length=1, max_length=120, pattern=r"^[a-z0-9-]+$")


# ============================================================
# UPDATE
# ============================================================

class StoreUpdate(BaseModel):
    """Campos actualizables de una tienda (todos opcionales)."""

    name: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = None
    logo_url: str | None = Field(default=None, max_length=500)
    banner_url: str | None = Field(default=None, max_length=500)
    phone: str | None = Field(default=None, max_length=30)
    email: EmailStr | None = None
    vertical: StoreVertical | None = None
    address: str | None = None
    city: str | None = Field(default=None, max_length=100)
    is_active: bool | None = None


# ============================================================
# READ
# ============================================================

class StoreRead(StoreBase):
    """Datos de la tienda que se devuelven al cliente."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    slug: str
    is_active: bool
    is_verified: bool
    rating_avg: float
    rating_count: int
    total_orders: int
    created_at: datetime
    updated_at: datetime


class StoreReadPublic(BaseModel):
    """
    Vista pública de una tienda.
    Oculta campos internos (commission_pct, owner_id).
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    name: str
    description: str | None = None
    logo_url: str | None = None
    banner_url: str | None = None
    phone: str | None = None
    email: EmailStr | None = None
    vertical: StoreVertical
    address: str | None = None
    city: str | None = None
    rating_avg: float
    rating_count: int
    total_orders: int
    is_verified: bool
    created_at: datetime