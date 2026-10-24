# ============================================================
# CONFIGURACIÓN DE LA APLICACIÓN
# ============================================================
# Usa Pydantic Settings para cargar variables de entorno
# desde el archivo .env con validación automática.

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Configuración central de la aplicación.
    Los valores se leen del archivo .env o de variables de entorno.
    """

    # ----------------------------------------------------------
    # GENERAL
    # ----------------------------------------------------------
    ENVIRONMENT: str = "development"
    PROJECT_NAME: str = "Macketi API"
    API_V1_PREFIX: str = "/api/v1"

    # ----------------------------------------------------------
    # BASE DE DATOS
    # ----------------------------------------------------------
    DATABASE_URL: str

    # ----------------------------------------------------------
    # REDIS
    # ----------------------------------------------------------
    #REDIS_URL: str

    # ----------------------------------------------------------
    # JWT
    # ----------------------------------------------------------
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 horas

    # ----------------------------------------------------------
    # CORS
    # ----------------------------------------------------------
    CORS_ORIGINS: str = "http://localhost:3000"

    # ----------------------------------------------------------
    # CONFIGURACIÓN DE PYDANTIC
    # ----------------------------------------------------------
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @property
    def cors_origins_list(self) -> list[str]:
        """Convierte la cadena de CORS en una lista."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    # ----------------------------------------------------------
    # WORDPRESS / WOOCOMMERCE (migración)
    # ----------------------------------------------------------
    WOOCOMMERCE_URL: str = ""
    WOOCOMMERCE_CONSUMER_KEY: str = ""
    WOOCOMMERCE_CONSUMER_SECRET: str = ""
    DOKAN_API_URL: str = ""

# Instancia única de configuración (se importa desde cualquier sitio)
settings = Settings()