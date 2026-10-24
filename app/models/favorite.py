# ============================================================
# MODELO: FAVORITE
# ============================================================
# Productos guardados como favoritos por un usuario.
#
# Diseño:
# - Tabla puente simple entre users y products.
# - UNIQUE (user_id, product_id) para evitar duplicados.
# - Sin soft delete: si se quita un favorito, se borra la fila.

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Favorite(Base, TimestampMixin):
    """Productos favoritos de un usuario."""

    __tablename__ = "favorites"

    # ----------------------------------------------------------
    # RESTRICCIONES
    # ----------------------------------------------------------
    __table_args__ = (
        UniqueConstraint("user_id", "product_id", name="uq_favorite_user_product"),
    )

    # ----------------------------------------------------------
    # IDENTIFICADOR
    # ----------------------------------------------------------
    id: Mapped[int] = mapped_column(primary_key=True)

    # ----------------------------------------------------------
    # RELACIONES
    # ----------------------------------------------------------
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    def __repr__(self) -> str:
        return f"<Favorite user_id={self.user_id} product_id={self.product_id}>"