# ============================================================
# MODELO: PRODUCT IMAGE
# ============================================================
# Imágenes asociadas a un producto.
#
# Diseño:
# - Un producto tiene N imágenes.
# - `position` define el orden (0 = imagen principal).
# - `is_primary` marca la imagen destacada del producto.
# - Más adelante se puede añadir `variation_id` para asociar
#   imágenes a variantes concretas (color rojo, talla M).

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.product import Product


class ProductImage(Base, TimestampMixin):
    """Imágenes de un producto."""

    __tablename__ = "product_images"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Producto al que pertenece la imagen.
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # URL de la imagen (S3, CDN o el que sea).
    url: Mapped[str] = mapped_column(String(500), nullable=False)

    # Texto alternativo (para SEO y accesibilidad).
    alt_text: Mapped[str | None] = mapped_column(String(255))

    # Orden dentro del producto (0 = primera).
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # ¿Es la imagen principal del producto?
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relación con el producto.
    product: Mapped[Product] = relationship(back_populates="images")

    def __repr__(self) -> str:
        return f"<ProductImage id={self.id} product_id={self.product_id}>"