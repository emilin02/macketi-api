# ============================================================
# CONEXIÓN A LA BASE DE DATOS
# ============================================================
# Configura SQLAlchemy con asyncpg para PostgreSQL.
#
# Patrón async obligatorio:
# - expire_on_commit=False es OBLIGATORIO en async.
#   Si no, al acceder a un atributo después de commit,
#   SQLAlchemy intenta recargar y lanza MissingGreenlet.
# - El dependency get_db gestiona el ciclo de vida de la sesión.
# - Los servicios llaman a flush(), nunca a commit().

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings


# ============================================================
# ENGINE
# ============================================================
# - pool_size: conexiones persistentes en el pool.
# - max_overflow: conexiones extra temporales.
# - pool_pre_ping: verifica que la conexión sigue viva antes de usarla.
# - pool_recycle: recicla conexiones cada 30 min (evita timeouts).
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.ENVIRONMENT == "development",  # log SQL en desarrollo
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=1800,
)


# ============================================================
# SESSION FACTORY
# ============================================================
# expire_on_commit=False: clave para async.
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ============================================================
# DEPENDENCY: get_db
# ============================================================
# Se inyecta en los endpoints con: db: AsyncSession = Depends(get_db)
async def get_db() -> AsyncIterator[AsyncSession]:
    """
    Proporciona una sesión de base de datos por request.
    Hace commit si todo va bien, rollback si hay error.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise