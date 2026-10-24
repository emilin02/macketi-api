# ============================================================
# SCHEMAS DE FAVORITO
# ============================================================

from datetime import datetime

from pydantic import BaseModel, ConfigDict


# ============================================================
# READ
# ============================================================

class FavoriteProductInfo(BaseModel):
    """Info resumida del producto favorito."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    name: str
    short_description: str | None = None
    rating_avg: float
    rating_count: int


class FavoriteRead(BaseModel):
    """Datos de un favorito."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    created_at: datetime