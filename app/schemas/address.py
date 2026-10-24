# ============================================================
# SCHEMAS DE DIRECCIÓN
# ============================================================
# Pydantic schemas para request/response de direcciones.

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ============================================================
# BASE
# ============================================================

class AddressBase(BaseModel):
    """Campos comunes a todos los schemas de dirección."""

    label: str = Field(min_length=1, max_length=60)
    recipient_name: str = Field(min_length=1, max_length=150)
    recipient_phone: str = Field(min_length=5, max_length=30)
    city: str = Field(min_length=1, max_length=100)
    neighborhood: str | None = Field(default=None, max_length=120)
    address_line: str = Field(min_length=1)
    reference: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    is_default: bool = False
    is_shipping: bool = True
    is_billing: bool = False


# ============================================================
# CREATE
# ============================================================

class AddressCreate(AddressBase):
    """Datos para crear una dirección nueva."""
    pass


# ============================================================
# UPDATE
# ============================================================

class AddressUpdate(BaseModel):
    """Campos actualizables de una dirección (todos opcionales)."""

    label: str | None = Field(default=None, min_length=1, max_length=60)
    recipient_name: str | None = Field(default=None, min_length=1, max_length=150)
    recipient_phone: str | None = Field(default=None, min_length=5, max_length=30)
    city: str | None = Field(default=None, min_length=1, max_length=100)
    neighborhood: str | None = Field(default=None, max_length=120)
    address_line: str | None = Field(default=None, min_length=1)
    reference: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    is_default: bool | None = None
    is_shipping: bool | None = None
    is_billing: bool | None = None


# ============================================================
# READ
# ============================================================

class AddressRead(AddressBase):
    """Datos de la dirección que se devuelven al cliente."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime