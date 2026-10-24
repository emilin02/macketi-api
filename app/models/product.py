# ============================================================
# MODELO: PRODUCT
# ============================================================
# Producto base del catálogo (modelo Amazon).
#
# Flujo de aprobación:
# - Un vendedor propone un producto → approval_status = PENDING.
# - El admin lo aprueba → approval_status = APPROVED.
# - El admin lo rechaza → approval_status = REJECTED + rejection_reason.
#
# Solo los productos aprobados aparecen en el catálogo público.

from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import Float, Integer

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.category import Category
    from app.models.brand import Brand
    from app.models.offer import Offer
    from app.models.product_image import ProductImage
    from app.models.attribute_value import AttributeValue
    from app.models.user import User
    from app.models.review import Review


# ============================================================
# ENUM DE ESTADO DE APROBACIÓN
# ============================================================

class ProductApprovalStatus(str, enum.Enum):
    """Estado de aprobación de un producto."""
    PENDING = "pending"      # esperando revisión del admin
    APPROVED = "approved"    # aprobado, visible en el catálogo
    REJECTED = "rejected"    # rechazado con motivo


# ============================================================
# MODELO
# ============================================================

class Product(Base, TimestampMixin):
    """Tabla de productos base (modelo Amazon)."""

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)

    # ----------------------------------------------------------
    # CLASIFICACIÓN
    # ----------------------------------------------------------
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    brand_id: Mapped[int | None] = mapped_column(
        ForeignKey("brands.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # ----------------------------------------------------------
    # IDENTIFICACIÓN
    # ----------------------------------------------------------
    slug: Mapped[str] = mapped_column(String(200), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    short_description: Mapped[str | None] = mapped_column(Text)

    # ----------------------------------------------------------
    # ESTADO
    # ----------------------------------------------------------
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # ----------------------------------------------------------
    # REPUTACIÓN
    # ----------------------------------------------------------
    # Se actualizan automáticamente al crear/editar/borrar reseñas.
    rating_avg: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    rating_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # ----------------------------------------------------------
    # APROBACIÓN
    # ----------------------------------------------------------
    # Los productos nuevos entran en PENDING hasta que el admin
    # los revise. Solo los APPROVED aparecen en el catálogo.
    approval_status: Mapped[ProductApprovalStatus] = mapped_column(
        SQLEnum(ProductApprovalStatus, name="product_approval_status"),
        default=ProductApprovalStatus.PENDING,
        nullable=False,
        index=True,
    )

    # Motivo del rechazo (solo si approval_status == REJECTED).
    rejection_reason: Mapped[str | None] = mapped_column(String(500))

    # Quién aprobó/rechazó y cuándo.
    reviewed_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Quién propuso el producto (para mostrar en el admin).
    proposed_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # ----------------------------------------------------------
    # RELACIONES
    # ----------------------------------------------------------
    category: Mapped["Category | None"] = relationship(back_populates="products")
    brand: Mapped["Brand | None"] = relationship(back_populates="products")
    offers: Mapped[list["Offer"]] = relationship(back_populates="product")
    images: Mapped[list["ProductImage"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="ProductImage.position",
    )
    attribute_values: Mapped[list["AttributeValue"]] = relationship(
        secondary="product_attribute_values",
        lazy="selectin",
    )
    reviews: Mapped[list["Review"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Product id={self.id} slug={self.slug} status={self.approval_status}>"