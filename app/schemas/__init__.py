# ============================================================
# SCHEMAS
# ============================================================
# Este archivo centraliza los exports de todos los schemas
# Pydantic de la aplicación.
#
# ¿Por qué centralizarlos?
# - Permite importar desde `app.schemas` en lugar de rutas largas.
# - Ejemplo: `from app.schemas import UserCreate, StoreCreate`
#   en lugar de `from app.schemas.user import UserCreate`.
#
# Cada schema está agrupado por módulo para mantenerlo ordenado.

# ------------------------------------------------------------
# USUARIOS
# ------------------------------------------------------------
from app.schemas.user import (
    UserBase,
    UserCreate,
    UserRead,
    UserUpdate,
)

# ------------------------------------------------------------
# AUTENTICACIÓN
# ------------------------------------------------------------
from app.schemas.auth import (
    LoginRequest,
    TokenResponse,
)

# ------------------------------------------------------------
# DIRECCIONES
# ------------------------------------------------------------
from app.schemas.address import (
    AddressBase,
    AddressCreate,
    AddressRead,
    AddressUpdate,
)

# ------------------------------------------------------------
# CATEGORÍAS
# ------------------------------------------------------------
from app.schemas.category import (
    CategoryBase,
    CategoryCreate,
    CategoryRead,
    CategoryTree,
    CategoryUpdate,
)

# ------------------------------------------------------------
# MARCAS
# ------------------------------------------------------------
from app.schemas.brand import (
    BrandBase,
    BrandCreate,
    BrandRead,
    BrandUpdate,
)

# ------------------------------------------------------------
# TIENDAS
# ------------------------------------------------------------
from app.schemas.store import (
    StoreBase,
    StoreCreate,
    StoreRead,
    StoreReadPublic,
    StoreUpdate,
)

# ------------------------------------------------------------
# OFERTAS
# ------------------------------------------------------------
from app.schemas.offer import (
    OfferBase,
    OfferCreate,
    OfferRead,
    OfferReadWithStore,
    OfferStoreInfo,
    OfferUpdate,
)

# ------------------------------------------------------------
# PRODUCTOS
# ------------------------------------------------------------
from app.schemas.product import (
    ProductBase,
    ProductCreate,
    ProductRead,
    ProductReadPublic,
    ProductReject,
    ProductUpdate,
    ProductWithOffers,
)

# ------------------------------------------------------------
# PEDIDOS
# ------------------------------------------------------------
from app.schemas.order import (
    OrderCreate,
    OrderItemCreate,
    OrderItemRead,
    OrderRead,
    OrderStatusUpdate,
)

# ------------------------------------------------------------
# RESEÑAS
# ------------------------------------------------------------
from app.schemas.review import (
    ReviewBase,
    ReviewBuyerInfo,
    ReviewCreate,
    ReviewRead,
    ReviewUpdate,
)
# ------------------------------------------------------------
# FAVORITOS
# ------------------------------------------------------------
from app.schemas.favorite import (
    FavoriteProductInfo,
    FavoriteRead,
)
# ------------------------------------------------------------
# CAMBIAR CONTRASEÑA
# ------------------------------------------------------------
from app.schemas.password import ChangePasswordRequest

# ------------------------------------------------------------
# ATTRIBUTES
# ------------------------------------------------------------

from app.schemas.attribute import (
    AttributeBase,
    AttributeCreate,
    AttributeRead,
    AttributeReadWithValues,
    AttributeUpdate,
    AttributeValueBase,
    AttributeValueCreate,
    AttributeValueRead,
    AttributeValueUpdate,
    ProductAttributesUpdate,
)


# ------------------------------------------------------------
# EXPORTS PÚBLICOS
# ------------------------------------------------------------
# __all__ define qué se exporta al hacer `from app.schemas import *`.
# No es obligatorio, pero ayuda a los linters y a la documentación.
__all__ = [
    # User
    "UserBase", "UserCreate", "UserRead", "UserUpdate",
    # Auth
    "LoginRequest", "TokenResponse",
    # Address
    "AddressBase", "AddressCreate", "AddressRead", "AddressUpdate",
    # Category
    "CategoryBase", "CategoryCreate", "CategoryRead", "CategoryTree", "CategoryUpdate",
    # Brand
    "BrandBase", "BrandCreate", "BrandRead", "BrandUpdate",
    # Store
    "StoreBase", "StoreCreate", "StoreRead", "StoreReadPublic", "StoreUpdate",
    # Offer
    "OfferBase", "OfferCreate", "OfferRead", "OfferReadWithStore",
    "OfferStoreInfo", "OfferUpdate",
    # Product
    "ProductBase", "ProductCreate", "ProductRead", "ProductReadPublic",
    "ProductReject", "ProductUpdate", "ProductWithOffers",
    # Order
    "OrderCreate", "OrderItemCreate", "OrderItemRead", "OrderRead", "OrderStatusUpdate",
    # Review
    "ReviewBase", "ReviewBuyerInfo", "ReviewCreate", "ReviewRead", "ReviewUpdate",
    # Favorite
    "FavoriteProductInfo", "FavoriteRead",
    # Password
    "ChangePasswordRequest",
    # Attribute
    "AttributeBase", "AttributeCreate", "AttributeRead", "AttributeReadWithValues",
    "AttributeUpdate", "AttributeValueBase", "AttributeValueCreate",
    "AttributeValueRead", "AttributeValueUpdate", "ProductAttributesUpdate",
]