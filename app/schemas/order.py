# ============================================================
# SCHEMAS DE PEDIDO
# ============================================================
# Pydantic schemas para request/response de pedidos.

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.order import OrderStatus, PaymentMethod


# ============================================================
# ORDER ITEM
# ============================================================

class OrderItemCreate(BaseModel):
    """Datos para crear una línea de pedido."""

    offer_id: int
    quantity: int = Field(gt=0)


class OrderItemRead(BaseModel):
    """Datos de una línea de pedido."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    offer_id: int
    store_id: int
    product_name: str
    product_slug: str
    product_image_url: str | None = None
    unit_price: float
    quantity: int
    line_total: float
    created_at: datetime


# ============================================================
# ORDER
# ============================================================

class OrderCreate(BaseModel):
    """
    Datos para crear un pedido.
    Se envía desde el carrito del cliente.
    """

    # Dirección de envío (el cliente elige una de sus direcciones).
    shipping_address_id: int

    # Items del pedido.
    items: list[OrderItemCreate] = Field(min_length=1)

    # Notas opcionales.
    customer_note: str | None = None

    # Método de pago.
    payment_method: PaymentMethod = PaymentMethod.COD


class OrderRead(BaseModel):
    """Datos completos de un pedido."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    order_number: str
    buyer_id: int

    # Dirección de envío (snapshot).
    shipping_recipient_name: str
    shipping_recipient_phone: str
    shipping_city: str
    shipping_neighborhood: str | None = None
    shipping_address_line: str
    shipping_reference: str | None = None

    # Estado y pago.
    status: OrderStatus
    payment_method: PaymentMethod

    # Importes.
    subtotal: float
    shipping_cost: float
    discount: float
    total: float
    currency: str

    # Notas.
    customer_note: str | None = None

    # Fechas.
    created_at: datetime
    updated_at: datetime
    confirmed_at: datetime | None = None
    shipped_at: datetime | None = None
    delivered_at: datetime | None = None
    cancelled_at: datetime | None = None

    # Items.
    items: list[OrderItemRead] = []


class OrderStatusUpdate(BaseModel):
    """Body para cambiar el estado de un pedido."""

    status: OrderStatus