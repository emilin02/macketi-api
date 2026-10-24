# ============================================================
# MODELO: STORE
# ============================================================
# Representa la tienda de un vendedor.
# (Versión completa la añadiremos después; esta es la base
# para que User pueda referenciarla.)

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SQLEnum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


# ============================================================
# ENUM DE VERTICALES
# ============================================================

class StoreVertical(str, enum.Enum):
    """Verticales de negocio disponibles en Macketi."""
    TIENDA = "tienda"
    FARMACIA = "farmacia"
    RESTAURANTE = "restaurante"
    SUPERMERCADO = "supermercado"


# ============================================================
# MODELO
# ============================================================

class Store(Base, TimestampMixin):
    """Tabla de tiendas (vendedores)."""

    __tablename__ = "stores"

    # Identificador
    id: Mapped[int] = mapped_column(primary_key=True)

    # Propietario
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Identificación pública
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    # Imágenes
    logo_url: Mapped[str | None] = mapped_column(String(500))
    banner_url: Mapped[str | None] = mapped_column(String(500))

    # Contacto
    phone: Mapped[str | None] = mapped_column(String(30))
    email: Mapped[str | None] = mapped_column(String(255))

    # Vertical
    vertical: Mapped[StoreVertical] = mapped_column(
        SQLEnum(StoreVertical, name="store_vertical"),
        default=StoreVertical.TIENDA,
        nullable=False,
        index=True,
    )

    # Ubicación
    address: Mapped[str | None] = mapped_column(Text)
    city: Mapped[str | None] = mapped_column(String(100), index=True)

    # Estado
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Reputación
    rating_avg: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    rating_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_orders: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Comisión específica (si aplica; si NULL, se usa la de la categoría)
    commission_pct: Mapped[float | None] = mapped_column(Float)

    # Soft delete
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relación con el propietario
    owner: Mapped["User"] = relationship(back_populates="stores")

    def __repr__(self) -> str:
        return f"<Store id={self.id} slug={self.slug} name={self.name}>"