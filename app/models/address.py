# ============================================================
# MODELO: ADDRESS
# ============================================================
# Direcciones de los usuarios.
#
# Diseño:
# - Un usuario puede tener N direcciones.
# - Cada dirección tiene un label ("Casa", "Trabajo", etc.).
# - `is_default` marca la dirección principal.
# - `is_shipping` y `is_billing` permiten separar roles.
# - Coordenadas lat/lng para el repartidor.
# - `reference` es un punto de referencia textual
#   (muy importante en Guinea Ecuatorial, donde las
#   direcciones postales no son comunes).

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class Address(Base, TimestampMixin):
    """Direcciones de los usuarios."""

    __tablename__ = "addresses"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Propietario de la dirección.
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ----------------------------------------------------------
    # ETIQUETA
    # ----------------------------------------------------------
    # "Casa", "Trabajo", "Oficina", "Casa de mamá"...
    label: Mapped[str] = mapped_column(String(60), nullable=False)

    # ----------------------------------------------------------
    # DATOS DE QUIEN RECIBE
    # ----------------------------------------------------------
    # Puede no ser el propio usuario (ej. enviar a un familiar).
    recipient_name: Mapped[str] = mapped_column(String(150), nullable=False)
    recipient_phone: Mapped[str] = mapped_column(String(30), nullable=False)

    # ----------------------------------------------------------
    # UBICACIÓN
    # ----------------------------------------------------------
    city: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    neighborhood: Mapped[str | None] = mapped_column(String(120))
    address_line: Mapped[str] = mapped_column(Text, nullable=False)
    reference: Mapped[str | None] = mapped_column(Text)

    # Coordenadas opcionales (para el repartidor).
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)

    # ----------------------------------------------------------
    # FLAGS
    # ----------------------------------------------------------
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_shipping: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_billing: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # ----------------------------------------------------------
    # SOFT DELETE
    # ----------------------------------------------------------
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # ----------------------------------------------------------
    # RELACIONES
    # ----------------------------------------------------------
    user: Mapped[User] = relationship(back_populates="addresses")

    def __repr__(self) -> str:
        return f"<Address id={self.id} user_id={self.user_id} label={self.label} city={self.city}>"