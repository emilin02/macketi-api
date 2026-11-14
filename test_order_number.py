import asyncio

from app.db.session import async_session_factory, engine
from app.api.v1.endpoints.orders import _generate_order_number


async def main():
    async with async_session_factory() as db:
        order_number = await _generate_order_number(db)

        print(f"Número de pedido generado: {order_number}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())