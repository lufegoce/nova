"""
Conector ERP simulado: no llama a ningún sistema externo, solo genera una
referencia falsa. Sirve para probar el flujo completo de NOVA (aprobar ->
pagar -> sincronizar con ERP) sin credenciales reales de SIIGO/Odoo/SAP, y
como plantilla mínima para implementar un ERP nuevo.
"""
import uuid

from app.services.erp.base import ConectorERP, DocumentoParaErp, ResultadoEnvioErp


class ConectorErpSimulado(ConectorERP):
    async def enviar_causacion(self, documento: DocumentoParaErp) -> ResultadoEnvioErp:
        return ResultadoEnvioErp(exitoso=True, referencia_erp=f"SIM-ERP-{uuid.uuid4().hex[:10]}")
