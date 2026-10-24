# ============================================================
# DEPENDENCIAS COMPARTIDAS
# ============================================================
# Se inyectan en los endpoints con Depends(...).

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User, UserRole


# ============================================================
# OAUTH2 SCHEME
# ============================================================
# Le dice a FastAPI dónde está el endpoint de login
# (para el botón "Authorize" del /docs).
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_PREFIX}/auth/token"
)


# ============================================================
# DEPENDENCIA: USUARIO ACTUAL
# ============================================================

async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """
    Devuelve el usuario autenticado a partir del JWT.
    Si el token es inválido o el usuario no existe, lanza 401.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Decodificar el token.
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    # Buscar el usuario en la BD.
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo",
        )

    return user


# Alias para usar en los endpoints.
CurrentUser = Annotated[User, Depends(get_current_user)]


# ============================================================
# DEPENDENCIA: USUARIO ADMIN
# ============================================================

async def get_current_admin(
    current_user: CurrentUser,
) -> User:
    """Verifica que el usuario actual es admin."""
    if UserRole.ADMIN not in current_user.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere rol de administrador",
        )
    return current_user


CurrentAdmin = Annotated[User, Depends(get_current_admin)]