# ============================================================
# MODELO: ATTRIBUTE VALUE
# ============================================================
# Valores posibles de cada atributo.
#
# Ejemplos:
#   - Color → Azul, Rojo, Negro
#   - Talla → S, M, L, XL, 42, 43
#   - Tapa → Dura, Blanda

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.attribute import Attribute


class AttributeValue(Base, TimestampMixin):
    """Valores posibles de un atributo."""

    __tablename__ = "attribute_values"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Atributo al que pertenece este valor.
    attribute_id: Mapped[int] = mapped_column(
        ForeignKey("attributes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Slug único dentro del atributo: azul, rojo, s, m, dura.
    slug: Mapped[str] = mapped_column(String(60), nullable=False)

    # Valor visible: "Azul", "Rojo", "S", "M", "Dura".
    value: Mapped[str] = mapped_column(String(120), nullable=False)

    # Orden dentro del atributo.
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relación con el atributo padre.
    attribute: Mapped[Attribute] = relationship(back_populates="values")

    def __repr__(self) -> str:
        return f"<AttributeValue id={self.id} attribute_id={self.attribute_id} value={self.value}>"