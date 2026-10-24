# ============================================================
# SCHEMAS DE MARCA
# ============================================================

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ============================================================
# BASE
# ============================================================

class BrandBase(BaseModel):
    """Campos comunes a todos los schemas de marca."""

    name: str = Field(min_length=1, max_length=150)
    description: str | None = None
    logo_url: str | None = Field(default=None, max_length=500)
    is_active: bool = True


# ============================================================
# CREATE
# ============================================================

class BrandCreate(BrandBase):
    """Datos para crear una marca."""

    slug: str = Field(min_length=1, max_length=120, pattern=r"^[a-z0-9-]+$")


# ============================================================
# UPDATE
# ============================================================

class BrandUpdate(BaseModel):
    """Campos actualizables de una marca."""

    name: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = None
    logo_url: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None


# ============================================================
# READ
# ============================================================

class BrandRead(BrandBase):
    """Datos de una marca."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    created_at: datetime
    updated_at: datetime