from fastapi import APIRouter

from app.api.v1.endpoints import (
    admin_products,
    addresses,
    attributes,
    auth,
    brands,
    categories,
    favorites,
    offers,
    orders,
    products,
    reviews,
    stores,
    users,
)


api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(addresses.router)
api_router.include_router(categories.router)
api_router.include_router(brands.router)
api_router.include_router(attributes.router)
api_router.include_router(stores.router)
api_router.include_router(products.router)
api_router.include_router(offers.router)
api_router.include_router(admin_products.router)
api_router.include_router(orders.router)
api_router.include_router(reviews.router)
api_router.include_router(favorites.router)