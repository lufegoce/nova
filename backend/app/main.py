"""
Punto de entrada de la API de NOVA (FastAPI).

Documentación Swagger automática disponible en /docs.
Al arrancar, lanza un listener de Redis Pub/Sub en background que reenvía
las notificaciones del worker Celery (ej. facturas nuevas de la DIAN) a los
clientes conectados por WebSocket.
"""
import asyncio
import json
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.auth import router as auth_router
from app.api.routes.facturas import router as facturas_router
from app.api.routes.dian import router as dian_router
from app.api.routes.configuracion import router as configuracion_router
from app.api.routes.seguridad import router as seguridad_router
from app.api.routes import websocket as websocket_module
from app.core.config import get_settings
from app.db.base import Base
from app.db.seed import sembrar_datos_prueba
from app.db.session import AsyncSessionLocal, engine
from app.workers.tasks import CANAL_NOTIFICACIONES_DIAN

settings = get_settings()


async def _crear_tablas_si_no_existen():
    """
    Creación de esquema para el MVP local. En producción, reemplazar por
    migraciones versionadas con Alembic (`alembic upgrade head`).
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as sesion:
        await sembrar_datos_prueba(sesion)


async def _escuchar_notificaciones_redis():
    cliente = aioredis.from_url(settings.REDIS_URL)
    pubsub = cliente.pubsub()
    await pubsub.subscribe(CANAL_NOTIFICACIONES_DIAN)

    async for mensaje in pubsub.listen():
        if mensaje["type"] != "message":
            continue
        payload = json.loads(mensaje["data"])
        tenant_id = payload.pop("tenant_id", "demo")
        await websocket_module.manager.notificar_tenant(tenant_id, payload)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await _crear_tablas_si_no_existen()
    tarea = asyncio.create_task(_escuchar_notificaciones_redis())
    yield
    tarea.cancel()


app = FastAPI(
    title=settings.APP_NAME,
    description="Plataforma de agentes autónomos para automatización financiera y contable.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    # Con cookies httpOnly, el navegador exige un origen exacto (no "*") cuando
    # allow_credentials=True.
    allow_origins=[settings.FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(facturas_router, prefix="/api/v1")
app.include_router(dian_router, prefix="/api/v1")
app.include_router(configuracion_router, prefix="/api/v1")
app.include_router(seguridad_router, prefix="/api/v1")
app.include_router(websocket_module.router)


@app.get("/health", tags=["sistema"])
async def health_check():
    return {"status": "ok", "app": settings.APP_NAME, "env": settings.ENV}
