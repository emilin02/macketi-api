# ============================================================
# MODELO: ORDER
# ============================================================
# Pedido de un comprador.
#
# Diseño:
# - Un pedido puede tener productos de varias tiendas.
# - Cada línea (OrderItem) referencia a una Offer.
# - Se guarda snapshot de nombre y precio por si cambian.
# - Estados: pending → confirmed → preparing → shipped → delivered.
# - Moneda: XAF por defecto (Franco CFA).

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.address import Address
    from app.models.order_item import OrderItem


# ============================================================
# ENUM DE ESTADOS
# ============================================================

class OrderStatus(str, enum.Enum):
    """Estados posibles de un pedido."""
    PENDING = "pending"          # esperando confirmación
    CONFIRMED = "confirmed"      # confirmado por el vendedor
    PREPARING = "preparing"      # en preparación (restaurante)
    SHIPPED = "shipped"          # enviado
    DELIVERED = "delivered"      # entregado
    CANCELLED = "cancelled"      # cancelado
    REFUNDED = "refunded"        # reembolsado


# ============================================================
# ENUM DE MÉTODO DE PAGO
# ============================================================

class PaymentMethod(str, enum.Enum):
    """Métodos de pago disponibles."""
    COD = "cod"                  # pago contra entrega
    TRANSFER = "transfer"        # transferencia bancaria
    CARD = "card"                # tarjeta
    WALLET = "wallet"            # cartera de la plataforma


# ============================================================
# MODELO
# ============================================================

class Order(Base, TimestampMixin):
    """Pedido de un comprador."""

    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)

    # ----------------------------------------------------------
    # NÚMERO DE PEDIDO (visible al usuario)
    # ----------------------------------------------------------
    # Formato: MK-2026-00001
    order_number: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
        index=True,
    )

    # ----------------------------------------------------------
    # COMPRADOR
    # ----------------------------------------------------------
    buyer_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # ----------------------------------------------------------
    # DIRECCIÓN DE ENVÍO
    # ----------------------------------------------------------
    # Copiamos los datos aquí (snapshot) por si el usuario
    # modifica o borra la dirección después.
    shipping_address_id: Mapped[int | None] = mapped_column(
        ForeignKey("addresses.id", ondelete="SET NULL"),
        nullable=True,
    )

    shipping_recipient_name: Mapped[str] = mapped_column(String(150), nullable=False)
    shipping_recipient_phone: Mapped[str] = mapped_column(String(30), nullable=False)
    shipping_city: Mapped[str] = mapped_column(String(100), nullable=False)
    shipping_neighborhood: Mapped[str | None] = mapped_column(String(120))
    shipping_address_line: Mapped[str] = mapped_column(Text, nullable=False)
    shipping_reference: Mapped[str | None] = mapped_column(Text)
    shipping_latitude: Mapped[float | None] = mapped_column()
    shipping_longitude: Mapped[float | None] = mapped_column()

    # ----------------------------------------------------------
    # ESTADO Y PAGO
    # ----------------------------------------------------------
    status: Mapped[OrderStatus] = mapped_column(
        SQLEnum(OrderStatus, name="order_status"),
        default=OrderStatus.PENDING,
        nullable=False,
        index=True,
    )

    payment_method: Mapped[PaymentMethod] = mapped_column(
        SQLEnum(PaymentMethod, name="payment_method"),
        default=PaymentMethod.COD,
        nullable=False,
    )

    # Referencia externa del pago (ID de transacción, etc.).
    payment_reference: Mapped[str | None] = mapped_column(String(120))

    # ----------------------------------------------------------
    # IMPORTES
    # ----------------------------------------------------------
    subtotal: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    shipping_cost: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    discount: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    total: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)

    currency: Mapped[str] = mapped_column(String(3), default="XAF", nullable=False)

    # ----------------------------------------------------------
    # NOTAS Y FECHAS
    # ----------------------------------------------------------
    customer_note: Mapped[str | None] = mapped_column(Text)

    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    shipped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # ----------------------------------------------------------
    # RELACIONES
    # ----------------------------------------------------------
    buyer: Mapped["User"] = relationship(
        back_populates="orders",
        foreign_keys=[buyer_id],
    )
    shipping_address: Mapped["Address | None"] = relationship()
    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Order id={self.id} number={self.order_number} status={self.status}>"