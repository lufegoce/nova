"""
Agente Conciliador: cruza movimientos bancarios contra facturas emitidas/causadas
y detecta discrepancias (montos, fechas, facturas sin pago asociado, etc).

En el MVP el extracto bancario se recibe como lista de transacciones ya
normalizadas (la integración real con Open Finance / API bancaria queda
como punto de extensión en app/services).
"""
from app.agents.base import AgenteBase
from app.models.documento import DocumentoFinanciero, EstadoDocumento
from sqlalchemy import select


class AgenteConciliador(AgenteBase):
    nombre = "agente_conciliador"

    async def ejecutar(self, movimientos_bancarios: list[dict]) -> dict:
        """
        movimientos_bancarios: [{"referencia": str, "valor": float, "fecha": str}, ...]
        Retorna un resumen: facturas conciliadas, discrepancias y sin coincidencia.
        """
        result = await self.db.execute(
            select(DocumentoFinanciero).where(
                DocumentoFinanciero.tenant_id == self.tenant_id,
                DocumentoFinanciero.estado.in_(
                    [EstadoDocumento.CAUSADO, EstadoDocumento.APROBACION_PENDIENTE]
                ),
            )
        )
        documentos_pendientes = result.scalars().all()

        conciliados, discrepancias, sin_match = [], [], []
        movimientos_por_ref = {m["referencia"]: m for m in movimientos_bancarios}

        for doc in documentos_pendientes:
            mov = movimientos_por_ref.get(doc.numero_factura)
            if mov is None:
                sin_match.append(str(doc.id))
                continue
            if abs(float(mov["valor"]) - float(doc.total)) > 0.01:
                discrepancias.append({
                    "documento_id": str(doc.id),
                    "valor_factura": float(doc.total),
                    "valor_banco": mov["valor"],
                })
            else:
                conciliados.append(str(doc.id))
                await self.registrar_evento(
                    doc.id,
                    accion="conciliacion_exitosa",
                    detalle=f"Cruce con movimiento bancario {mov['referencia']}",
                    resultado={"valor": mov["valor"]},
                )

        for disc in discrepancias:
            await self.registrar_evento(
                disc["documento_id"],
                accion="discrepancia_conciliacion",
                detalle="Valor en banco no coincide con el total facturado",
                resultado=disc,
            )

        return {
            "conciliados": conciliados,
            "discrepancias": discrepancias,
            "sin_match": sin_match,
        }
