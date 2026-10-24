# ============================================================
# MODELO: REVIEW
# ============================================================
# Reseñas de productos escritas por compradores.
#
# Diseño:
# - Solo usuarios que hayan comprado pueden reseñar (compra verificada).
# - Una reseña por producto y comprador (UNIQUE constraint).
# - rating de 1 a 5 estrellas.
# - is_published permite al admin ocultar reseñas inapropiadas.
# - Al crear/editar/borrar, se recalcula Product.rating_avg.
#
# Nota: en el futuro se puede extender para reseñar vendedores
# (store_id) además de productos.

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.product import Product
    from app.models.order import Order


class Review(Base, TimestampMixin):
    """Reseñas de productos."""

    __tablename__ = "reviews"

    # ----------------------------------------------------------
    # RESTRICCIONES
    # ----------------------------------------------------------
    __table_args__ = (
        # Un comprador solo puede dejar UNA reseña por producto.
        UniqueConstraint("buyer_id", "product_id", name="uq_review_buyer_product"),
        # El rating debe estar entre 1 y 5.
        CheckConstraint("rating >= 1 AND rating <= 5", name="ck_review_rating_range"),
    )

    # ----------------------------------------------------------
    # IDENTIFICADOR
    # ----------------------------------------------------------
    id: Mapped[int] = mapped_column(primary_key=True)

    # ----------------------------------------------------------
    # RELACIONES
    # ----------------------------------------------------------
    # Quién escribe la reseña.
    buyer_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Sobre qué producto.
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # De qué pedido viene (para verificar compra).
    # Puede ser NULL si el pedido se borra.
    order_id: Mapped[int | None] = mapped_column(
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True,
    )

    # ----------------------------------------------------------
    # CONTENIDO
    # ----------------------------------------------------------
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)

    # ----------------------------------------------------------
    # ESTADO
    # ----------------------------------------------------------
    is_verified_purchase: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    is_published: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, index=True
    )

    # ----------------------------------------------------------
    # RELACIONES ORM
    # ----------------------------------------------------------
    buyer: Mapped["User"] = relationship()
    product: Mapped["Product"] = relationship(back_populates="reviews")
    order: Mapped["Order | None"] = relationship()

    def __repr__(self) -> str:
        return f"<Review id={self.id} product_id={self.product_id} rating={self.rating}>"