"""
Agente Reportero: genera informes financieros en tiempo real (KPIs de eficiencia
y errores) a partir del estado actual de los documentos del tenant.
"""
from sqlalchemy import func, select

from app.agents.base import AgenteBase
from app.models.documento import DocumentoFinanciero, EstadoDocumento


class AgenteReportero(AgenteBase):
    nombre = "agente_reportero"

    async def ejecutar(self) -> dict:
        result = await self.db.execute(
            select(DocumentoFinanciero.estado, func.count(), func.coalesce(func.sum(DocumentoFinanciero.total), 0))
            .where(DocumentoFinanciero.tenant_id == self.tenant_id)
            .group_by(DocumentoFinanciero.estado)
        )
        filas = result.all()

        resumen_por_estado = {
            estado.value: {"cantidad": cantidad, "total": float(total)}
            for estado, cantidad, total in filas
        }

        total_documentos = sum(v["cantidad"] for v in resumen_por_estado.values())
        con_error = resumen_por_estado.get(EstadoDocumento.CON_ERROR.value, {}).get("cantidad", 0)
        tasa_error = round(con_error / total_documentos, 4) if total_documentos else 0.0

        return {
            "total_documentos": total_documentos,
            "por_estado": resumen_por_estado,
            "tasa_error": tasa_error,
        }
