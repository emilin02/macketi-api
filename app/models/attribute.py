# ============================================================
# MODELO: ATTRIBUTE
# ============================================================
# Define los TIPOS de atributo (Color, Talla, Tapa, etc.).
#
# Ejemplos:
#   - Color
#   - Talla
#   - Tapa (dura/blanda)
#   - Material

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.attribute_value import AttributeValue


class Attribute(Base, TimestampMixin):
    """Tipos de atributo (Color, Talla, etc.)."""

    __tablename__ = "attributes"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Slug único para URLs y filtros: color, talla, tapa, material.
    slug: Mapped[str] = mapped_column(String(60), unique=True, nullable=False, index=True)

    # Nombre visible: "Color", "Talla", "Tapa".
    name: Mapped[str] = mapped_column(String(80), nullable=False)

    # Orden de aparición en los filtros.
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Estado.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relación con los valores.
    values: Mapped[list[AttributeValue]] = relationship(
        back_populates="attribute",
        cascade="all, delete-orphan",
        order_by="AttributeValue.position",
    )

    def __repr__(self) -> str:
        return f"<Attribute id={self.id} slug={self.slug} name={self.name}>"