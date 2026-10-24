# ============================================================
# MODELO: BRAND
# ============================================================
# Marcas de productos.
#
# Diseño:
# - Slug único para URLs.
# - Logo opcional.
# - is_active para ocultar sin borrar.

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.product import Product


class Brand(Base, TimestampMixin):
    """Tabla de marcas."""

    __tablename__ = "brands"

    # Identificador
    id: Mapped[int] = mapped_column(primary_key=True)

    # Identificación
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    logo_url: Mapped[str | None] = mapped_column(String(500))

    # Estado
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relaciones
    products: Mapped[list["Product"]] = relationship(back_populates="brand")

    def __repr__(self) -> str:
        return f"<Brand id={self.id} slug={self.slug} name={self.name}>"