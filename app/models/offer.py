# ============================================================
# MODELO: OFFER
# ============================================================
# Representa la oferta de un vendedor sobre un producto.

# Esta línea hace que TODAS las anotaciones de tipo se traten
# como strings por defecto, evitando problemas con forward
# references y con Pylance.
from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

# Imports solo para type checking (evita imports circulares).
if TYPE_CHECKING:
    from app.models.product import Product
    from app.models.store import Store


# ============================================================
# ENUM DE CONDICIÓN
# ============================================================

class OfferCondition(str, enum.Enum):
    """Condición del producto en esta oferta."""
    NEW = "new"
    REFURBISHED = "refurbished"
    USED = "used"


# ============================================================
# ENUM DE ESTADO
# ============================================================

class OfferStatus(str, enum.Enum):
    """Estado de la oferta."""
    ACTIVE = "active"
    PAUSED = "paused"
    OUT_OF_STOCK = "out_of_stock"
    ARCHIVED = "archived"


# ============================================================
# MODELO
# ============================================================

class Offer(Base, TimestampMixin):
    """Tabla de ofertas (una por vendedor y producto)."""

    __tablename__ = "offers"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Relaciones
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    store_id: Mapped[int] = mapped_column(
        ForeignKey("stores.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Precio y stock
    price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    compare_price: Mapped[float | None] = mapped_column(Numeric(12, 2))

    stock: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    stock_unlimited: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Condición y estado
    condition: Mapped[OfferCondition] = mapped_column(
        SQLEnum(OfferCondition, name="offer_condition"),
        default=OfferCondition.NEW,
        nullable=False,
    )

    status: Mapped[OfferStatus] = mapped_column(
        SQLEnum(OfferStatus, name="offer_status"),
        default=OfferStatus.ACTIVE,
        nullable=False,
        index=True,
    )

    # SKU y código de barras
    sku: Mapped[str | None] = mapped_column(String(80), index=True)
    barcode: Mapped[str | None] = mapped_column(String(80))

    # Flags por vertical
    requires_prescription: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    prep_time_min: Mapped[int | None] = mapped_column(Integer)

    # Soft delete
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relaciones ORM
    product: Mapped[Product] = relationship(back_populates="offers")
    store: Mapped[Store] = relationship()

    def __repr__(self) -> str:
        return f"<Offer id={self.id} product_id={self.product_id} store_id={self.store_id} price={self.price}>"