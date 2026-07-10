"""
Sesión de base de datos async (SQLAlchemy 2.0 + asyncpg).

Aislamiento multi-tenant: en este MVP se usa una columna `tenant_id` en cada
tabla (estrategia "shared DB, shared schema, row-level tenant"). Para clientes
enterprise que requieran aislamiento físico, cambiar DATABASE_URL por tenant
y resolverlo en `get_db` a partir del header X-Tenant-Id.
"""
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

settings = get_settings()

engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
