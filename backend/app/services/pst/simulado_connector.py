"""Conector PST simulado: para probar el flujo de NOVA sin credenciales reales de Factus."""
from datetime import datetime, timedelta

from app.services.pst.base import ConectorPST, DocumentoRecibidoPst, FiltrosDocumentosRecibidos

# CUFE fijo (no aleatorio) para que llamadas repetidas devuelvan los mismos
# documentos — así se puede probar la deduplicación por CUFE del job de
# sincronización igual que pasaría con un PST real.
_CUFE_SIM_1 = "sim-0000000000000000000000000000000000000001"
_CUFE_SIM_2 = "sim-0000000000000000000000000000000000000002"


class ConectorPstSimulado(ConectorPST):
    async def listar_recibidos(self, filtros: FiltrosDocumentosRecibidos) -> list[DocumentoRecibidoPst]:
        hoy = datetime.utcnow()
        documentos = [
            DocumentoRecibidoPst(
                cufe=_CUFE_SIM_1,
                nit_emisor="900111222",
                razon_social_emisor="Proveedor Simulado SAS",
                numero_documento="FE-SIM-1",
                fecha_emision=(hoy - timedelta(days=1)).date().isoformat(),
                tiene_eventos_pendientes=True,
                datos_crudos={"modo_simulado": True},
            ),
            DocumentoRecibidoPst(
                cufe=_CUFE_SIM_2,
                nit_emisor="900333444",
                razon_social_emisor="Servicios Simulados SAS",
                numero_documento="FE-SIM-2",
                fecha_emision=(hoy - timedelta(days=3)).date().isoformat(),
                tiene_eventos_pendientes=False,
                datos_crudos={"modo_simulado": True},
            ),
        ]
        if filtros.cufe:
            documentos = [d for d in documentos if d.cufe == filtros.cufe]
        if filtros.nit_emisor:
            documentos = [d for d in documentos if d.nit_emisor == filtros.nit_emisor]
        if filtros.solo_con_eventos_pendientes is not None:
            documentos = [d for d in documentos if d.tiene_eventos_pendientes == filtros.solo_con_eventos_pendientes]
        return documentos

    async def probar_conexion(self) -> None:
        return None
