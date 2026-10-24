# ============================================================
# SCHEMAS DE ATRIBUTO
# ============================================================

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ============================================================
# ATTRIBUTE VALUE
# ============================================================

class AttributeValueBase(BaseModel):
    """Campos comunes a los schemas de valor de atributo."""

    value: str = Field(min_length=1, max_length=120)
    position: int = 0


class AttributeValueCreate(AttributeValueBase):
    """Datos para crear un valor de atributo."""

    slug: str = Field(min_length=1, max_length=60, pattern=r"^[a-z0-9-]+$")


class AttributeValueUpdate(BaseModel):
    """Campos actualizables de un valor de atributo."""

    value: str | None = Field(default=None, min_length=1, max_length=120)
    position: int | None = None


class AttributeValueRead(AttributeValueBase):
    """Datos de un valor de atributo."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    attribute_id: int
    slug: str
    created_at: datetime
    updated_at: datetime


# ============================================================
# ATTRIBUTE
# ============================================================

class AttributeBase(BaseModel):
    """Campos comunes a los schemas de atributo."""

    name: str = Field(min_length=1, max_length=80)
    position: int = 0
    is_active: bool = True


class AttributeCreate(AttributeBase):
    """Datos para crear un atributo."""

    slug: str = Field(min_length=1, max_length=60, pattern=r"^[a-z0-9-]+$")
    values: list[AttributeValueCreate] = []


class AttributeUpdate(BaseModel):
    """Campos actualizables de un atributo."""

    name: str | None = Field(default=None, min_length=1, max_length=80)
    position: int | None = None
    is_active: bool | None = None


class AttributeRead(AttributeBase):
    """Datos de un atributo sin valores."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    created_at: datetime
    updated_at: datetime


class AttributeReadWithValues(AttributeRead):
    """Atributo con sus valores anidados."""

    values: list[AttributeValueRead] = []


# ============================================================
# ASIGNAR ATRIBUTOS A PRODUCTO
# ============================================================

class ProductAttributesUpdate(BaseModel):
    """Body para reemplazar los atributos de un producto."""

    value_ids: list[int] = Field(
        default_factory=list,
        description="IDs de los valores de atributo asignados.",
    )