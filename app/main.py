# ============================================================
# PUNTO DE ENTRADA DE FASTAPI
# ============================================================
# Aquí se crea la aplicación, se configuran los middlewares
# y se incluyen los routers de la API.

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from sqlalchemy import text
from app.db.session import async_session_factory

# ============================================================
# ROUTERS
# ============================================================
from app.api.v1.router import api_router

# ============================================================
# CREAR APLICACIÓN
# ============================================================
app = FastAPI(
    title=settings.PROJECT_NAME,
    version="0.1.0",
    description="API central de Macketi - Marketplace multivendedor",
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
)


# ============================================================
# MIDDLEWARES
# ============================================================
# CORS: permite que el frontend (Next.js en localhost:3000)
# haga peticiones a esta API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# HEALTH CHECK
# ============================================================
@app.get("/health", tags=["health"])
async def health_check():
    """Endpoint para verificar que la API está viva."""
    return {"status": "ok", "environment": settings.ENVIRONMENT}


# ============================================================
# ROUTERS
# ============================================================
# Aquí se incluirán los routers cuando los creemos.
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


# ============================================================
# HEALTH CHECK CON BASE DE DATOS
# ===
@app.get("/health/db", tags=["health"])
async def health_check_db():
    """Verifica que la API puede conectar con PostgreSQL."""
    try:
        async with async_session_factory() as session:
            result = await session.execute(text("SELECT 1"))
            value = result.scalar()
        return {"status": "ok", "db_result": value}
    except Exception as e:
        return {"status": "error", "detail": str(e)}