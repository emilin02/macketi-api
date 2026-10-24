# ============================================================
# ENDPOINTS DE CATEGORÍAS
# ============================================================
# CRUD de categorías jerárquicas.
#
# Endpoints públicos:
#   - GET /categories            (listar raíz)
#   - GET /categories/tree       (árbol completo)
#   - GET /categories/{slug}     (obtener por slug)
#   - GET /categories/{slug}/children (subcategorías)
#
# Endpoints admin:
#   - POST /categories           (crear)
#   - PATCH /categories/{id}     (actualizar)
#   - DELETE /categories/{id}    (desactivar)

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentAdmin
from app.db.session import get_db
from app.models.category import Category
from app.schemas.category import (
    CategoryCreate,
    CategoryRead,
    CategoryTree,
    CategoryUpdate,
)

router = APIRouter(prefix="/categories", tags=["categories"])


# ============================================================
# HELPER: CONSTRUIR ÁRBOL
# ============================================================
def _build_tree(
    categories: list[Category],
    parent_id: int | None = None,
) -> list[CategoryTree]:
    """
    Convierte una lista plana de categorías en un árbol jerárquico.

    IMPORTANTE: no accedemos a `cat.children` porque es una relación
    lazy y en async da MissingGreenlet. En su lugar, construimos el
    árbol manualmente con recursión sobre la lista plana.
    """
    tree: list[CategoryTree] = []

    for cat in categories:
        if cat.parent_id == parent_id:
            node = CategoryTree(
                id=cat.id,
                slug=cat.slug,
                name=cat.name,
                description=cat.description,
                image_url=cat.image_url,
                icon_url=cat.icon_url,
                vertical=cat.vertical,
                position=cat.position,
                is_active=cat.is_active,
                parent_id=cat.parent_id,
                created_at=cat.created_at,
                updated_at=cat.updated_at,
                children=[],  # se rellena abajo con recursión
            )
            node.children = _build_tree(categories, cat.id)
            tree.append(node)

    # Ordenar por position y luego por nombre.
    tree.sort(key=lambda c: (c.position, c.name))
    return tree


# ============================================================
# LISTAR CATEGORÍAS RAÍZ (público)
# ============================================================
@router.get(
    "",
    response_model=list[CategoryRead],
    summary="Listar categorías raíz",
)
async def list_categories(
    db: Annotated[AsyncSession, Depends(get_db)],
    vertical: str | None = None,
) -> list[Category]:
    """Devuelve las categorías raíz activas."""
    stmt = (
        select(Category)
        .where(Category.parent_id.is_(None))
        .where(Category.is_active.is_(True))
        .order_by(Category.position, Category.name)
    )
    if vertical:
        stmt = stmt.where(Category.vertical == vertical)

    result = await db.execute(stmt)
    return list(result.scalars().all())


# ============================================================
# ÁRBOL COMPLETO (público)
# ============================================================
@router.get(
    "/tree",
    response_model=list[CategoryTree],
    summary="Árbol completo de categorías",
)
async def get_categories_tree(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[CategoryTree]:
    """Devuelve todas las categorías activas en formato árbol."""
    result = await db.execute(
        select(Category)
        .where(Category.is_active.is_(True))
        .order_by(Category.position, Category.name)
    )
    categories = list(result.scalars().all())
    return _build_tree(categories)


# ============================================================
# OBTENER UNA CATEGORÍA POR SLUG (público)
# ============================================================
@router.get(
    "/{slug}",
    response_model=CategoryRead,
    summary="Obtener una categoría por slug",
)
async def get_category(
    slug: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Category:
    """Devuelve una categoría por su slug."""
    result = await db.execute(
        select(Category).where(Category.slug == slug)
    )
    category = result.scalar_one_or_none()

    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categoría no encontrada",
        )

    return category


# ============================================================
# SUBCATEGORÍAS (público)
# ============================================================
@router.get(
    "/{slug}/children",
    response_model=list[CategoryRead],
    summary="Subcategorías de una categoría",
)
async def get_category_children(
    slug: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[Category]:
    """Devuelve las subcategorías directas de una categoría."""
    # Buscar la categoría padre.
    result = await db.execute(
        select(Category).where(Category.slug == slug)
    )
    parent = result.scalar_one_or_none()

    if parent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categoría no encontrada",
        )

    # Buscar las hijas.
    result = await db.execute(
        select(Category)
        .where(Category.parent_id == parent.id)
        .where(Category.is_active.is_(True))
        .order_by(Category.position, Category.name)
    )
    return list(result.scalars().all())


# ============================================================
# CREAR CATEGORÍA (admin)
# ============================================================
@router.post(
    "",
    response_model=CategoryRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear una categoría (admin)",
)
async def create_category(
    data: CategoryCreate,
    current_admin: CurrentAdmin,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Category:
    """Crea una categoría nueva. Solo admin."""
    # Verificar que el slug no exista.
    result = await db.execute(
        select(Category).where(Category.slug == data.slug)
    )
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una categoría con ese slug",
        )

    # Si tiene parent_id, verificar que exista.
    if data.parent_id is not None:
        result = await db.execute(
            select(Category).where(Category.id == data.parent_id)
        )
        if result.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La categoría padre no existe",
            )

    category = Category(**data.model_dump())
    db.add(category)
    await db.flush()
    await db.refresh(category)

    return category


# ============================================================
# ACTUALIZAR CATEGORÍA (admin)
# ============================================================
@router.patch(
    "/{category_id}",
    response_model=CategoryRead,
    summary="Actualizar una categoría (admin)",
)
async def update_category(
    category_id: int,
    data: CategoryUpdate,
    current_admin: CurrentAdmin,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Category:
    """Actualiza una categoría. Solo admin."""
    result = await db.execute(
        select(Category).where(Category.id == category_id)
    )
    category = result.scalar_one_or_none()

    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categoría no encontrada",
        )

    # Aplicar solo los campos enviados.
    update_data = data.model_dump(exclude_unset=True)

    # Si se cambia el slug, verificar que no exista.
    if "slug" in update_data and update_data["slug"] != category.slug:
        result = await db.execute(
            select(Category).where(Category.slug == update_data["slug"])
        )
        if result.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya existe una categoría con ese slug",
            )

    # Evitar que una categoría sea su propia padre.
    if update_data.get("parent_id") == category.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Una categoría no puede ser su propia padre",
        )

    for field, value in update_data.items():
        setattr(category, field, value)

    await db.flush()
    await db.refresh(category)

    return category


# ============================================================
# ELIMINAR CATEGORÍA (admin, soft delete)
# ============================================================
@router.delete(
    "/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar una categoría (admin)",
)
async def delete_category(
    category_id: int,
    current_admin: CurrentAdmin,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Desactiva una categoría. Solo admin."""
    result = await db.execute(
        select(Category).where(Category.id == category_id)
    )
    category = result.scalar_one_or_none()

    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categoría no encontrada",
        )

    category.is_active = False
    await db.flush()

# ============================================================
# PRODUCTOS DE UNA CATEGORÍA (público)
# ============================================================

from app.models.product import Product, ProductApprovalStatus
from app.schemas.product import ProductReadPublic


@router.get(
    "/{slug}/products",
    response_model=list[ProductReadPublic],
    summary="Productos de una categoría",
)
async def get_category_products(
    slug: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = 20,
    offset: int = 0,
) -> list[Product]:
    """
    Devuelve los productos aprobados de una categoría.
    Incluye también los productos de las subcategorías.
    """
    # Buscar la categoría padre.
    result = await db.execute(
        select(Category).where(Category.slug == slug)
    )
    category = result.scalar_one_or_none()

    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categoría no encontrada",
        )

    # Obtener IDs de la categoría y sus subcategorías directas.
    result = await db.execute(
        select(Category.id).where(Category.parent_id == category.id)
    )
    subcategory_ids = [row[0] for row in result.all()]
    category_ids = [category.id, *subcategory_ids]

    # Buscar productos.
    result = await db.execute(
        select(Product)
        .where(Product.category_id.in_(category_ids))
        .where(Product.is_active.is_(True))
        .where(Product.approval_status == ProductApprovalStatus.APPROVED)
        .order_by(Product.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())