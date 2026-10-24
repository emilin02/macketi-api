# ============================================================
# MODELO: ORDER ITEM
# ============================================================
# Cada línea de un pedido.
#
# Diseño:
# - Referencia a la OFERTA (no al producto).
# - Guarda snapshot del nombre y precio (por si cambian).
# - Lleva store_id para saber a qué tienda va cada línea.

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.order import Order
    from app.models.offer import Offer
    from app.models.store import Store


class OrderItem(Base, TimestampMixin):
    """Línea de un pedido."""

    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Pedido al que pertenece.
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Oferta comprada.
    offer_id: Mapped[int] = mapped_column(
        ForeignKey("offers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Tienda (para agrupar pedidos por tienda fácilmente).
    store_id: Mapped[int] = mapped_column(
        ForeignKey("stores.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # ----------------------------------------------------------
    # SNAPSHOT
    # ----------------------------------------------------------
    # Guardamos estos datos para que el pedido histórico no cambie
    # si el vendedor edita el producto después.
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    product_slug: Mapped[str] = mapped_column(String(200), nullable=False)
    product_image_url: Mapped[str | None] = mapped_column(String(500))

    # ----------------------------------------------------------
    # PRECIO Y CANTIDAD
    # ----------------------------------------------------------
    unit_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    line_total: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)

    # ----------------------------------------------------------
    # RELACIONES
    # ----------------------------------------------------------
    order: Mapped[Order] = relationship(back_populates="items")
    offer: Mapped[Offer] = relationship()
    store: Mapped[Store] = relationship()

    def __repr__(self) -> str:
        return f"<OrderItem id={self.id} order_id={self.order_id} offer_id={self.offer_id}>"