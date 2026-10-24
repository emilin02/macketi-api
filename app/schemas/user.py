# ============================================================
# SCHEMAS DE USUARIO
# ============================================================
# Pydantic schemas para request/response de usuarios.

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import UserRole


# ============================================================
# BASE
# ============================================================

class UserBase(BaseModel):
    """Campos comunes a todos los schemas de usuario."""
    email: EmailStr
    full_name: str | None = None
    phone: str | None = None


# ============================================================
# CREATE (registro)
# ============================================================

class UserCreate(UserBase):
    """Datos para registrar un usuario nuevo."""
    password: str = Field(min_length=8, max_length=100)
    # Por defecto, todo el que se registra es comprador.
    # Si quiere ser vendedor, se cambia después.
    roles: list[UserRole] = [UserRole.BUYER]


# ============================================================
# READ (response)
# ============================================================

class UserRead(UserBase):
    """Datos del usuario que se devuelven al cliente."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    roles: list[UserRole]
    is_active: bool
    email_verified: bool
    avatar_url: str | None = None
    created_at: datetime


# ============================================================
# UPDATE
# ============================================================

class UserUpdate(BaseModel):
    """Campos actualizables del usuario."""
    full_name: str | None = None
    phone: str | None = None
    avatar_url: str | None = None