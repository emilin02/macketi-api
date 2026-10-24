# ============================================================
# SCHEMAS DE CATEGORÍA
# ============================================================

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.store import StoreVertical


# ============================================================
# BASE
# ============================================================

class CategoryBase(BaseModel):
    """Campos comunes a todos los schemas de categoría."""

    slug: str = Field(min_length=1, max_length=120)
    name: str = Field(min_length=1, max_length=150)
    description: str | None = None
    image_url: str | None = Field(default=None, max_length=500)
    icon_url: str | None = Field(default=None, max_length=500)
    vertical: StoreVertical | None = None
    position: int = 0
    is_active: bool = True


# ============================================================
# CREATE
# ============================================================

class CategoryCreate(CategoryBase):
    """Datos para crear una categoría."""

    parent_id: int | None = None


# ============================================================
# UPDATE
# ============================================================

class CategoryUpdate(BaseModel):
    """Campos actualizables (todos opcionales)."""

    slug: str | None = Field(default=None, min_length=1, max_length=120)
    name: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = None
    image_url: str | None = Field(default=None, max_length=500)
    icon_url: str | None = Field(default=None, max_length=500)
    vertical: StoreVertical | None = None
    parent_id: int | None = None
    position: int | None = None
    is_active: bool | None = None


# ============================================================
# READ
# ============================================================

class CategoryRead(CategoryBase):
    """Datos que se devuelven al cliente."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    parent_id: int | None = None
    created_at: datetime
    updated_at: datetime


# ============================================================
# TREE (jerárquico)
# ============================================================

class CategoryTree(CategoryRead):
    """Categoría con sus subcategorías anidadas."""

    children: list["CategoryTree"] = []

CategoryTree.model_rebuild()