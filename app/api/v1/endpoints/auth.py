# ============================================================
# ENDPOINTS DE AUTENTICACIÓN
# ============================================================

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.user import UserCreate, UserRead


router = APIRouter(prefix="/auth", tags=["auth"])


# ============================================================
# REGISTRO
# ============================================================

@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar un usuario nuevo",
)
async def register(
    data: UserCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Crea un usuario nuevo en la plataforma."""
    # Normalizar email a minúsculas.
    email = data.email.lower()

    # Comprobar si ya existe.
    result = await db.execute(select(User).where(User.email == email))
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un usuario con ese email",
        )

    # Crear el usuario.
    user = User(
        email=email,
        password_hash=hash_password(data.password),
        full_name=data.full_name,
        phone=data.phone,
        roles=data.roles,
    )

    db.add(user)
    await db.flush()   # asigna id sin commit
    await db.refresh(user)

    return user


# ============================================================
# LOGIN
# ============================================================

@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Iniciar sesión",
)
async def login(
    data: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """Verifica credenciales y devuelve un JWT."""
    # Buscar el usuario por email.
    result = await db.execute(
        select(User).where(User.email == data.email.lower())
    )
    user = result.scalar_one_or_none()

    if user is None or not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo",
        )

    # Crear el token.
    token = create_access_token(subject=user.id)

    return TokenResponse(access_token=token, user=user)


# ============================================================
# USUARIO ACTUAL
# ============================================================

@router.get(
    "/me",
    response_model=UserRead,
    summary="Obtener el usuario autenticado",
)
async def me(current_user: CurrentUser) -> User:
    """Devuelve los datos del usuario autenticado."""
    return current_user

# ============================================================
# LOGIN PARA SWAGGER (form-data)
# ============================================================

from fastapi.security import OAuth2PasswordRequestForm

@router.post(
    "/token",
    response_model=TokenResponse,
    summary="Login para Swagger UI (OAuth2 form-data)",
    include_in_schema=True,
)
async def login_swagger(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """
    Endpoint de login compatible con el botón Authorize de Swagger.
    Acepta form-data (grant_type, username, password) en lugar de JSON.
    """
    # Buscar el usuario por email (username en OAuth2 es el email).
    result = await db.execute(
        select(User).where(User.email == form_data.username.lower())
    )
    user = result.scalar_one_or_none()

    if user is None or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo",
        )

    token = create_access_token(subject=user.id)

    return TokenResponse(access_token=token, user=user)