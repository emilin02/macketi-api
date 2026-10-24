# ============================================================
# CONFIGURACIÓN DE ALEMBIC
# ============================================================
# Este script se ejecuta cuando corres `alembic revision` o
# `alembic upgrade`. Se encarga de:
# 1. Leer la URL de la base de datos desde settings.
# 2. Cargar los modelos SQLAlchemy para que Alembic sepa
#    qué tablas hay que crear/modificar.
# 3. Ejecutar las migraciones en modo async.
#
# SOLUCIÓN A LARGO PLAZO PARA ENUMS:
# - Alembic no gestiona bien los tipos ENUM de PostgreSQL
#   cuando se reutilizan en varias tablas (intenta crearlos
#   varias veces y da error "ya existe un tipo").
# - La solución es decirle a Alembic que NO compare ni gestione
#   los tipos ENUM automáticamente.
# - Los ENUMs se crean a mano en la primera migración y se
#   reutilizan en las siguientes con `create_type=False`.

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context


# ------------------------------------------------------------
# IMPORTS DE LA APLICACIÓN
# ------------------------------------------------------------
from app.core.config import settings
from app.db.base import Base


# ------------------------------------------------------------
# IMPORTS DE MODELOS
# ------------------------------------------------------------
# IMPORTANTE: importar TODOS los modelos aquí para que Alembic
# los detecte al generar las migraciones.
# Cada vez que crees un modelo nuevo, impórtalo aquí.
from app.models.user import User  # noqa: F401
from app.models.store import Store  # noqa: F401
from app.models.category import Category  # noqa: F401
from app.models.brand import Brand  # noqa: F401
from app.models.product import Product  # noqa: F401
from app.models.offer import Offer  # noqa: F401
from app.models.product_image import ProductImage  # noqa: F401
from app.models.attribute import Attribute  # noqa: F401
from app.models.attribute_value import AttributeValue  # noqa: F401
from app.models.product_attribute_value import ProductAttributeValue  # noqa: F401
from app.models.address import Address  # noqa: F401
from app.models.order import Order, OrderStatus, PaymentMethod  # noqa: F401
from app.models.order_item import OrderItem  # noqa: F401ç
from app.models.review import Review  # noqa: F401
from app.models.favorite import Favorite  # noqa: F401
# ------------------------------------------------------------
# CONFIGURACIÓN DE LOGGING
# ------------------------------------------------------------
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


# ------------------------------------------------------------
# METADATA DE LOS MODELOS
# ------------------------------------------------------------
target_metadata = Base.metadata


# ------------------------------------------------------------
# FUNCIÓN AUXILIAR: INCLUIR OBJETOS
# ------------------------------------------------------------
# Esta función se llama para cada objeto de la base de datos.
# Sirve para ignorar objetos que no queremos que Alembic gestione
# (como los tipos ENUM, que gestionamos a mano).
def include_object(object, name, type_, reflected, compare_to):
    """
    Filtra qué objetos debe considerar Alembic al comparar la BD
    con los modelos.

    - type_ == "type": es un tipo (ENUM, etc.).
    - Si devolvemos False, Alembic lo ignora.

    Devolvemos False para los tipos ENUM, así Alembic no intenta
    crear/destruir tipos que ya existen. Los gestionamos a mano
    en las migraciones con `create_type=False`.
    """
    if type_ == "type":
        return False
    return True


# ------------------------------------------------------------
# EJECUCIÓN OFFLINE (sin conexión a la BD)
# ------------------------------------------------------------
def run_migrations_offline() -> None:
    """
    Genera el SQL sin conectarse a la BD.
    Útil para revisar los cambios antes de aplicarlos.
    """
    url = settings.DATABASE_URL
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


# ------------------------------------------------------------
# EJECUCIÓN ONLINE (con conexión a la BD)
# ------------------------------------------------------------
def do_run_migrations(connection: Connection) -> None:
    """
    Ejecuta las migraciones sobre una conexión activa.

    Opciones clave:
    - include_object: filtra los tipos ENUM (no los gestiona).
    - compare_type: detecta cambios de tipo en columnas.
    - compare_server_default: detecta cambios en valores por defecto.
    """
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_object=include_object,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Crea un engine async y ejecuta las migraciones."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        url=settings.DATABASE_URL,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Punto de entrada para migraciones online (async)."""
    asyncio.run(run_async_migrations())


# ------------------------------------------------------------
# EJECUTAR
# ------------------------------------------------------------
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()