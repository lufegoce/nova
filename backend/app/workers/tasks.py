"""
Tareas asíncronas de Celery.

`consultar_dian_task` corre en un worker separado del proceso de FastAPI, por
lo que no puede llamar directamente al ConnectionManager en memoria del
WebSocket. Para comunicar ambos procesos se usa Redis Pub/Sub: el worker
publica el evento, y un listener en el proceso de FastAPI (ver app/main.py)
lo reenvía a los clientes conectados.
"""
import asyncio
import json

import redis
from sqlalchemy import select

from app.core.config import get_settings
from app.services.dian_connector import consultar_facturas_nuevas, enviar_acuse_recibo
from app.workers.celery_app import celery_app

settings = get_settings()

CANAL_NOTIFICACIONES_DIAN = "nova:notificaciones:dian"


def _publicar_notificacion(tenant_id: str, payload: dict) -> None:
    cliente_redis = redis.from_url(settings.REDIS_URL)
    cliente_redis.publish(CANAL_NOTIFICACIONES_DIAN, json.dumps({"tenant_id": tenant_id, **payload}))


@celery_app.task(name="app.workers.tasks.consultar_dian_task")
def consultar_dian_task(tenant_id: str = "demo") -> dict:
    """
    Simula la consulta periódica a la DIAN. Al encontrar facturas nuevas,
    envía el Acuse de Recibo automático y notifica al Command Center vía WS.
    """
    facturas = consultar_facturas_nuevas()

    for factura in facturas:
        acuse = enviar_acuse_recibo(factura["numero_factura"])
        _publicar_notificacion(
            tenant_id,
            {
                "evento": "factura_nueva_dian",
                "factura": factura,
                "acuse": acuse,
            },
        )

    return {"facturas_procesadas": len(facturas)}


@celery_app.task(name="app.workers.tasks.escanear_seguridad_task")
def escanear_seguridad_task() -> dict:
    """
    Corre el Agente de Seguridad para cada tenant con actividad reciente.
    No hay tabla de tenants todavía (ver TODO en app/api/deps.py sobre
    resolver tenant desde JWT/API key en vez de header libre); mientras
    tanto, se descubren los tenants activos a partir de documentos_financieros.
    """
    return asyncio.run(_escanear_seguridad_todos_los_tenants())


async def _escanear_seguridad_todos_los_tenants() -> dict:
    from app.agents.agente_seguridad import AgenteSeguridad
    from app.db.session import AsyncSessionLocal
    from app.models.documento import DocumentoFinanciero

    resultados = {}
    async with AsyncSessionLocal() as db:
        tenants = (await db.execute(select(DocumentoFinanciero.tenant_id).distinct())).scalars().all()

        for tenant_id in tenants:
            agente = AgenteSeguridad(db, tenant_id)
            resultados[tenant_id] = await agente.ejecutar_escaneo()

    return resultados


@celery_app.task(name="app.workers.tasks.procesar_lote_facturas_task")
def procesar_lote_facturas_task(tenant_id: str, rutas_xml: list[str]) -> dict:
    """
    Placeholder para procesamiento masivo (ej. 1000 facturas en fin de mes).
    La lógica de ingesta real vive en AgenteReceptor/AgenteContable, que son
    async; este task orquesta la ejecución en lote fuera del ciclo de vida
    de una sola request HTTP.
    """
    return {"tenant_id": tenant_id, "total_recibidas": len(rutas_xml), "estado": "encolado"}
