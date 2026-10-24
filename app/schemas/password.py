# ============================================================
# SCHEMAS DE CONTRASEÑA
# ============================================================

from pydantic import BaseModel, Field, model_validator


class ChangePasswordRequest(BaseModel):
    """Body para cambiar la contraseña del usuario autenticado."""

    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=100)

    @model_validator(mode="after")
    def check_passwords_differ(self) -> "ChangePasswordRequest":
        """Verifica que la nueva contraseña es distinta a la actual."""
        if self.current_password == self.new_password:
            raise ValueError(
                "La nueva contraseña debe ser distinta a la actual"
            )
        return self