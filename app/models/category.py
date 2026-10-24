# ============================================================
# MODELO: CATEGORY
# ============================================================
# Categorías jerárquicas para organizar los productos.
#
# Diseño:
# - Jerarquía con parent_id (una categoría puede tener subcategorías).
# - Vertical opcional (NULL = aplica a todas las verticales).
# - Slug único para URLs amigables.
# - Position para ordenar entre hermanas.

from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.store import StoreVertical

if TYPE_CHECKING:
    from app.models.product import Product


class Category(Base, TimestampMixin):
    """Tabla de categorías jerárquicas."""

    __tablename__ = "categories"

    # ----------------------------------------------------------
    # IDENTIFICADOR
    # ----------------------------------------------------------
    id: Mapped[int] = mapped_column(primary_key=True)

    # ----------------------------------------------------------
    # JERARQUÍA
    # ----------------------------------------------------------
    # parent_id = NULL → categoría raíz.
    # parent_id = X   → subcategoría de X.
    # ON DELETE SET NULL: si se borra el padre, las hijas pasan a ser raíz.
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # ----------------------------------------------------------
    # IDENTIFICACIÓN
    # ----------------------------------------------------------
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(String(500))
    icon_url: Mapped[str | None] = mapped_column(String(500))

    # ----------------------------------------------------------
    # VERTICAL
    # ----------------------------------------------------------
    # NULL = aplica a todas las verticales.
    vertical: Mapped[StoreVertical | None] = mapped_column(
        SQLEnum(StoreVertical, name="store_vertical"),
        nullable=True,
        index=True,
    )

    # ----------------------------------------------------------
    # ORDEN Y ESTADO
    # ----------------------------------------------------------
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # ----------------------------------------------------------
    # RELACIONES
    # ----------------------------------------------------------
    # Subcategorías (relación auto-referencial).
    children: Mapped[list["Category"]] = relationship(
        back_populates="parent",
    )
    parent: Mapped["Category | None"] = relationship(
        back_populates="children",
        remote_side="Category.id",
    )

    # Productos de esta categoría.
    products: Mapped[list["Product"]] = relationship(back_populates="category")

    def __repr__(self) -> str:
        return f"<Category id={self.id} slug={self.slug} name={self.name}>"