# ============================================================
# MODELO: PRODUCT ATTRIBUTE VALUE
# ============================================================
# Tabla puente entre productos y valores de atributo.
#
# Sirve para saber qué atributos tiene cada producto.
#
# Ejemplo:
#   Producto "Camiseta Joma Azul Talla M"
#     → attribute_value = "Azul"  (de atributo "Color")
#     → attribute_value = "M"      (de atributo "Talla")

from __future__ import annotations

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ProductAttributeValue(Base):
    """Relación N:M entre productos y valores de atributo."""

    __tablename__ = "product_attribute_values"

    # Clave compuesta: producto + valor de atributo.
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        primary_key=True,
    )
    attribute_value_id: Mapped[int] = mapped_column(
        ForeignKey("attribute_values.id", ondelete="CASCADE"),
        primary_key=True,
    )

    def __repr__(self) -> str:
        return f"<ProductAttributeValue product_id={self.product_id} value_id={self.attribute_value_id}>"