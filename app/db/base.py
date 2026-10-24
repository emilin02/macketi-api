# ============================================================
# BASE DECLARATIVA DE SQLALCHEMY
# ============================================================
# Todos los modelos heredan de esta clase.
# Alembic lee Base.metadata para generar las migraciones.
#
# IMPORTANTE: este archivo NO debe importar modelos.
# Los modelos se importan desde alembic/env.py para evitar
# imports circulares.

from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Clase base para todos los modelos SQLAlchemy."""
    pass


class TimestampMixin:
    """
    Mixin que añade campos de auditoría (created_at, updated_at).
    Se puede heredar en cualquier modelo que necesite trazabilidad.
    """

    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )