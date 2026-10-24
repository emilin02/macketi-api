# ============================================================
# MODELO: USER
# ============================================================
# Representa a cualquier persona que usa la plataforma:
# compradores, vendedores y administradores.
#
# Diseño:
# - Un solo modelo con roles (buyer, vendor, admin).
# - Un usuario puede tener varios roles a la vez.
# - Email único (case-insensitive en la BD).
# - Contraseñas hasheadas con bcrypt.
# - Soft delete (deleted_at) en lugar de borrado físico.

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum as SQLEnum, String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

# Importamos Store solo para type checking (evita import circular).
if TYPE_CHECKING:
    from app.models.store import Store
    from app.models.address import Address
    from app.models.order import Order

# ============================================================
# ENUM DE ROLES
# ============================================================

class UserRole(str, enum.Enum):
    """Roles disponibles en la plataforma."""
    BUYER = "buyer"      # comprador
    VENDOR = "vendor"    # vendedor (puede tener tienda)
    ADMIN = "admin"      # administrador de la plataforma


# ============================================================
# MODELO
# ============================================================

class User(Base, TimestampMixin):
    """
    Tabla de usuarios.
    Incluye compradores, vendedores y administradores.
    """

    __tablename__ = "users"

    # ----------------------------------------------------------
    # IDENTIFICADOR
    # ----------------------------------------------------------
    id: Mapped[int] = mapped_column(primary_key=True)

    # ----------------------------------------------------------
    # CREDENCIALES
    # ----------------------------------------------------------
    # Email único. Se guarda en minúsculas para evitar duplicados
    # del tipo "Juan@x.com" vs "juan@x.com".
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    # Hash de la contraseña (bcrypt). NUNCA se guarda en claro.
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # ----------------------------------------------------------
    # DATOS PERSONALES
    # ----------------------------------------------------------
    full_name: Mapped[str | None] = mapped_column(String(150))
    phone: Mapped[str | None] = mapped_column(String(30))
    avatar_url: Mapped[str | None] = mapped_column(String(500))

    # ----------------------------------------------------------
    # ROLES
    # ----------------------------------------------------------
    # Un usuario puede tener varios roles (buyer + vendor, etc.).
    # Usamos ARRAY de PostgreSQL para simplicidad.
    roles: Mapped[list[UserRole]] = mapped_column(
        ARRAY(SQLEnum(UserRole, name="user_role")),
        default=[UserRole.BUYER],
        nullable=False,
    )

    # ----------------------------------------------------------
    # ESTADO
    # ----------------------------------------------------------
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # ----------------------------------------------------------
    # AUDITORÍA
    # ----------------------------------------------------------
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # ----------------------------------------------------------
    # RELACIONES
    # ----------------------------------------------------------
    # Un usuario puede tener varias tiendas (si es vendor).
    stores: Mapped[list["Store"]] = relationship(
        back_populates="owner",
        cascade="all, delete-orphan",
    )
    addresses: Mapped[list[Address]] = relationship(
    back_populates="user",
    cascade="all, delete-orphan",
    )
    orders: Mapped[list[Order]] = relationship(
    back_populates="buyer",
    foreign_keys="Order.buyer_id",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email}>"