# ============================================================
# ENDPOINTS DE PEDIDOS
# ============================================================

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select, text
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentAdmin, CurrentUser
from app.db.session import get_db
from app.models.address import Address
from app.models.offer import Offer, OfferStatus
from app.models.order import Order, OrderStatus, PaymentMethod
from app.models.order_item import OrderItem
from app.models.store import Store
from app.models.user import UserRole
from app.schemas.order import OrderCreate, OrderRead, OrderStatusUpdate


router = APIRouter(prefix="/orders", tags=["orders"])


# ============================================================
# HELPER: GENERAR NÚMERO DE PEDIDO
# ============================================================

async def _generate_order_number(db: AsyncSession) -> str:
    """
    Genera un número de pedido único en formato MK-YYYY-NNNNN
    utilizando una secuencia de PostgreSQL.
    """
    year = datetime.now(timezone.utc).year

    result = await db.execute(
        text("SELECT nextval('order_number_seq')")
    )

    sequence_number = result.scalar_one()

    return f"MK-{year}-{sequence_number:05d}"


# ============================================================
# CREAR PEDIDO (comprador)
# ============================================================

@router.post(
    "",
    response_model=OrderRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un pedido desde el carrito",
)
async def create_order(
    data: OrderCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Order:
    """
    Crea un pedido a partir del carrito del cliente.
    - Valida que la dirección de envío pertenezca al usuario.
    - Valida que cada oferta exista, esté activa y tenga stock.
    - Descuenta el stock de cada oferta.
    - Calcula totales.
    """
    # ----------------------------------------------------------
    # 1. Validar la dirección de envío.
    # ----------------------------------------------------------
    result = await db.execute(
        select(Offer)
        .where(Offer.id == item_data.offer_id)
        .where(Offer.deleted_at.is_(None))
        .with_for_update(of=Offer)
    )
    address = result.scalar_one_or_none()

    if address is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dirección de envío no encontrada",
        )

    # Validar que no existan ofertas repetidas.
    offer_ids = [item.offer_id for item in data.items]

    if len(offer_ids) != len(set(offer_ids)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se permiten ofertas repetidas en un mismo pedido",
        )



    # ----------------------------------------------------------
    # 2. Validar las ofertas y calcular totales.
    # ----------------------------------------------------------
    subtotal = 0.0
    order_items_to_create: list[dict] = []

    for item_data in sorted(
        data.items,
        key=lambda item: item.offer_id
    ):
        # Buscar la oferta.
        result = await db.execute(
            select(Offer)
            .options(selectinload(Offer.store))
            .where(Offer.id == item_data.offer_id)
            .where(Offer.deleted_at.is_(None))
        )
        offer = result.scalar_one_or_none()

        if offer is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Oferta {item_data.offer_id} no encontrada",
            )

        if offer.status != OfferStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"La oferta {item_data.offer_id} no está activa",
            )

        # Verificar stock.
        if not offer.stock_unlimited and offer.stock < item_data.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Stock insuficiente para la oferta {item_data.offer_id}",
            )

        # Buscar el producto para el snapshot.
        # Nota: usamos lazy load aquí porque ya tenemos offer.product_id.
        from app.models.product import Product
        result = await db.execute(
            select(Product)
            .options(selectinload(Product.images))
            .where(Product.id == offer.product_id)
        )
        product = result.scalar_one_or_none()

        if product is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Producto de la oferta {item_data.offer_id} no encontrado",
            )

        # Calcular total de la línea.
        unit_price = float(offer.price)
        line_total = unit_price * item_data.quantity
        subtotal += line_total

        # Preparar el item.
        image_url = product.images[0].url if product.images else None
        order_items_to_create.append({
            "offer_id": offer.id,
            "store_id": offer.store_id,
            "product_name": product.name,
            "product_slug": product.slug,
            "product_image_url": image_url,
            "unit_price": unit_price,
            "quantity": item_data.quantity,
            "line_total": line_total,
        })

        # Descontar stock.
        if not offer.stock_unlimited:
            offer.stock -= item_data.quantity
            if offer.stock == 0:
                offer.status = OfferStatus.OUT_OF_STOCK

    # ----------------------------------------------------------
    # 3. Crear el pedido.
    # ----------------------------------------------------------
    order_number = await _generate_order_number(db)

    order = Order(
        order_number=order_number,
        buyer_id=current_user.id,
        shipping_address_id=address.id,
        # Snapshot de la dirección.
        shipping_recipient_name=address.recipient_name,
        shipping_recipient_phone=address.recipient_phone,
        shipping_city=address.city,
        shipping_neighborhood=address.neighborhood,
        shipping_address_line=address.address_line,
        shipping_reference=address.reference,
        shipping_latitude=address.latitude,
        shipping_longitude=address.longitude,
        # Estado y pago.
        status=OrderStatus.PENDING,
        payment_method=data.payment_method,
        # Importes.
        subtotal=subtotal,
        shipping_cost=0.0,
        discount=0.0,
        total=subtotal,
        currency="XAF",
        # Notas.
        customer_note=data.customer_note,
    )

    db.add(order)
    await db.flush()

    # ----------------------------------------------------------
    # 4. Crear los items del pedido.
    # ----------------------------------------------------------
    for item_dict in order_items_to_create:
        order_item = OrderItem(
            order_id=order.id,
            **item_dict,
        )
        db.add(order_item)

    await db.flush()

    # Recargar el pedido con sus items.
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.id == order.id)
    )
    return result.scalar_one()


# ============================================================
# MIS PEDIDOS (comprador)
# ============================================================

@router.get(
    "/me",
    response_model=list[OrderRead],
    summary="Mis pedidos (comprador)",
)
async def list_my_orders(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[Order]:
    """Lista los pedidos del usuario autenticado."""
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.buyer_id == current_user.id)
        .order_by(Order.created_at.desc())
    )
    return list(result.scalars().all())


# ============================================================
# PEDIDOS DE MIS TIENDAS (vendedor)
# ============================================================

@router.get(
    "/store/me",
    response_model=list[OrderRead],
    summary="Pedidos de mis tiendas (vendedor)",
)
async def list_store_orders(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[Order]:
    """Lista los pedidos que incluyen productos de las tiendas del vendedor."""
    # Obtener los IDs de las tiendas del usuario.
    result = await db.execute(
        select(Store.id)
        .where(Store.owner_id == current_user.id)
        .where(Store.deleted_at.is_(None))
    )
    store_ids = [row[0] for row in result.all()]

    if not store_ids:
        return []

    # Buscar los pedidos que tengan al menos un item de esas tiendas.
    result = await db.execute(
        select(Order)
        .join(OrderItem, OrderItem.order_id == Order.id)
        .options(selectinload(Order.items))
        .where(OrderItem.store_id.in_(store_ids))
        .distinct()
        .order_by(Order.created_at.desc())
    )
    return list(result.scalars().all())


# ============================================================
# OBTENER UN PEDIDO POR NÚMERO
# ============================================================

@router.get(
    "/{order_number}",
    response_model=OrderRead,
    summary="Obtener un pedido por número",
)
async def get_order(
    order_number: str,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Order:
    """
    Devuelve un pedido por su número.
    Solo el comprador, un vendedor implicado o un admin pueden verlo.
    """
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.order_number == order_number)
    )
    order = result.scalar_one_or_none()

    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pedido no encontrado",
        )

    # Permisos.
    is_admin = UserRole.ADMIN in current_user.roles
    is_buyer = order.buyer_id == current_user.id

    # Obtener las tiendas del usuario.
    result = await db.execute(
        select(Store.id).where(Store.owner_id == current_user.id)
    )
    my_store_ids = {row[0] for row in result.all()}
    is_seller = any(item.store_id in my_store_ids for item in order.items)

    if not (is_admin or is_buyer or is_seller):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para ver este pedido",
        )

    return order


# ============================================================
# CANCELAR PEDIDO (comprador)
# ============================================================

@router.post(
    "/{order_number}/cancel",
    response_model=OrderRead,
    summary="Cancelar un pedido (comprador)",
)
async def cancel_order(
    order_number: str,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Order:
    """
    Cancela un pedido. Solo el comprador y solo si está en PENDING.
    Devuelve el stock a las ofertas.
    """
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.order_number == order_number)
    )
    order = result.scalar_one_or_none()

    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pedido no encontrado",
        )

    if order.buyer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el comprador puede cancelar este pedido",
        )

    if order.status != OrderStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se pueden cancelar pedidos en estado PENDING",
        )

    # Devolver el stock a las ofertas.
    for item in order.items:
        result = await db.execute(
            select(Offer).where(Offer.id == item.offer_id)
        )
        offer = result.scalar_one_or_none()
        if offer and not offer.stock_unlimited:
            offer.stock += item.quantity
            if offer.status == OfferStatus.OUT_OF_STOCK and offer.stock > 0:
                offer.status = OfferStatus.ACTIVE

    order.status = OrderStatus.CANCELLED
    order.cancelled_at = datetime.now(timezone.utc)

    await db.flush()
    await db.refresh(order)

    return order


# ============================================================
# CAMBIAR ESTADO DEL PEDIDO (vendedor o admin)
# ============================================================

@router.patch(
    "/{order_number}/status",
    response_model=OrderRead,
    summary="Cambiar el estado de un pedido",
)
async def update_order_status(
    order_number: str,
    data: OrderStatusUpdate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Order:
    """
    Cambia el estado de un pedido.
    Solo el vendedor implicado o un admin pueden hacerlo.
    """
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.order_number == order_number)
    )
    order = result.scalar_one_or_none()

    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pedido no encontrado",
        )

    # Permisos.
    is_admin = UserRole.ADMIN in current_user.roles
    result = await db.execute(
        select(Store.id).where(Store.owner_id == current_user.id)
    )
    my_store_ids = {row[0] for row in result.all()}
    is_seller = any(item.store_id in my_store_ids for item in order.items)

    if not (is_admin or is_seller):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para cambiar el estado de este pedido",
        )

    # Aplicar el cambio de estado.
    order.status = data.status

    # Registrar la fecha correspondiente.
    now = datetime.now(timezone.utc)
    if data.status == OrderStatus.CONFIRMED:
        order.confirmed_at = now
    elif data.status == OrderStatus.SHIPPED:
        order.shipped_at = now
    elif data.status == OrderStatus.DELIVERED:
        order.delivered_at = now
    elif data.status == OrderStatus.CANCELLED:
        order.cancelled_at = now

    await db.flush()
    await db.refresh(order)

    return order


# ============================================================
# LISTAR TODOS LOS PEDIDOS (admin)
# ============================================================

@router.get(
    "",
    response_model=list[OrderRead],
    summary="Listar todos los pedidos (admin)",
)
async def list_all_orders(
    current_admin: CurrentAdmin,
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = 50,
    offset: int = 0,
) -> list[Order]:
    """Lista todos los pedidos del sistema. Solo admin."""
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.items))
        .order_by(Order.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())