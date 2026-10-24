# ============================================================
# ENDPOINTS DE USUARIO
# ============================================================
# Gestión del perfil del usuario autenticado.
# Incluye: ver perfil, actualizar perfil, cambiar contraseña.

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.security import hash_password, verify_password
from app.db.session import get_db
from app.models.user import User
from app.schemas.password import ChangePasswordRequest
from app.schemas.user import UserRead, UserUpdate


router = APIRouter(prefix="/users", tags=["users"])


# ============================================================
# OBTENER MI PERFIL
# ============================================================

@router.get(
    "/me",
    response_model=UserRead,
    summary="Obtener mi perfil",
)
async def get_my_profile(current_user: CurrentUser) -> User:
    """Devuelve el perfil del usuario autenticado."""
    return current_user


# ============================================================
# ACTUALIZAR MI PERFIL
# ============================================================

@router.patch(
    "/me",
    response_model=UserRead,
    summary="Actualizar mi perfil",
)
async def update_my_profile(
    data: UserUpdate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """
    Actualiza el perfil del usuario autenticado.
    Solo permite cambiar: full_name, phone, avatar_url.
    El email y los roles NO se pueden cambiar desde aquí.
    """
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(current_user, field, value)

    await db.flush()
    await db.refresh(current_user)

    return current_user


# ============================================================
# CAMBIAR MI CONTRASEÑA
# ============================================================

@router.post(
    "/me/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cambiar mi contraseña",
)
async def change_my_password(
    data: ChangePasswordRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """
    Cambia la contraseña del usuario autenticado.

    Requiere:
    - La contraseña actual (para verificar identidad).
    - La nueva contraseña (mínimo 8 caracteres).
    - Que la nueva sea distinta a la actual.
    """
    # Verificar la contraseña actual.
    if not verify_password(data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña actual es incorrecta",
        )

    # Hashear y guardar la nueva contraseña.
    current_user.password_hash = hash_password(data.new_password)

    await db.flush()