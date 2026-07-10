"""
Clase base para todos los agentes de NOVA.

Diseño clave: cada agente es STATELESS (no guarda estado propio en memoria
entre invocaciones) para permitir escalado horizontal bajo demanda en picos
de fin de mes. Todo el estado vive en Postgres (documento + eventos_auditoria).

Cada acción de un agente queda registrada en EventoAuditoria (trazabilidad
inmutable), lo que permite al Chat Inteligente responder preguntas como
"¿por qué no se pagó la factura 123?".
"""
from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.documento import EventoAuditoria


class AgenteBase(ABC):
    nombre: str = "agente_base"

    def __init__(self, db: AsyncSession, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    async def registrar_evento(
        self,
        documento_id: UUID,
        accion: str,
        detalle: str | None = None,
        resultado: dict | None = None,
    ) -> EventoAuditoria:
        evento = EventoAuditoria(
            tenant_id=self.tenant_id,
            documento_id=documento_id,
            agente=self.nombre,
            accion=accion,
            detalle=detalle,
            resultado=resultado,
            creado_en=datetime.utcnow(),
        )
        self.db.add(evento)
        await self.db.flush()
        return evento

    @abstractmethod
    async def ejecutar(self, *args, **kwargs):
        ...
