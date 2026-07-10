"""
Agente Contable: aplica reglas contables (PUC), calcula retenciones
(ReteFuente, ICA) y valida requisitos DIAN antes de causar el documento.

Aprendizaje simple: si ya existe una ReglaClasificacionPuc para el NIT del
emisor (guardada cuando un humano corrigió la cuenta PUC al aprobar una
factura anterior — ver /facturas/{id}/aprobar), se usa esa cuenta
directamente y NO se llama a Claude. La confianza es alta porque viene de una
corrección humana explícita, así que el documento pasa a CAUSADO sin marcar
revisión adicional. Si no hay regla, se clasifica como antes (Claude o
default) y puede quedar en APROBACION_PENDIENTE.
"""
from uuid import UUID

from sqlalchemy import select

from app.agents.base import AgenteBase
from app.models.aprendizaje import ReglaClasificacionPuc
from app.models.documento import DocumentoFinanciero, EstadoDocumento
from app.services.claude_enrichment import clasificar_factura_con_claude
from app.services.retenciones import calcular_reteica, calcular_retefuente


class AgenteContable(AgenteBase):
    nombre = "agente_contable"

    async def aprender_correccion_humana(self, documento: DocumentoFinanciero, cuenta_puc_corregida: str) -> None:
        """
        Guarda/actualiza la regla aprendida para el NIT del emisor tras una
        corrección humana explícita al momento de aprobar. La próxima factura
        del mismo NIT usará esta cuenta directamente (ver `ejecutar`).
        """
        regla = await self._buscar_regla_aprendida(documento.nit_emisor)
        cuenta_anterior = documento.cuenta_puc_sugerida

        if regla is None:
            regla = ReglaClasificacionPuc(
                tenant_id=self.tenant_id,
                nit_emisor=documento.nit_emisor,
                cuenta_puc=cuenta_puc_corregida,
                veces_aplicada=0,
            )
            self.db.add(regla)
        else:
            regla.cuenta_puc = cuenta_puc_corregida

        documento.cuenta_puc_sugerida = cuenta_puc_corregida
        await self.db.flush()

        await self.registrar_evento(
            documento.id,
            accion="correccion_humana_cuenta_puc",
            detalle=f"Cuenta PUC corregida de '{cuenta_anterior}' a '{cuenta_puc_corregida}'; regla guardada para NIT {documento.nit_emisor}",
            resultado={"cuenta_anterior": cuenta_anterior, "cuenta_nueva": cuenta_puc_corregida},
        )

    async def _buscar_regla_aprendida(self, nit_emisor: str) -> ReglaClasificacionPuc | None:
        result = await self.db.execute(
            select(ReglaClasificacionPuc).where(
                ReglaClasificacionPuc.tenant_id == self.tenant_id,
                ReglaClasificacionPuc.nit_emisor == nit_emisor,
            )
        )
        return result.scalar_one_or_none()

    async def ejecutar(
        self,
        documento_id: UUID,
        concepto_retefuente: str = "compras_generales",
        tarifa_reteica_por_mil: float = 6.9,
    ) -> DocumentoFinanciero:
        documento = await self.db.get(DocumentoFinanciero, documento_id)
        if documento is None or documento.tenant_id != self.tenant_id:
            raise ValueError(f"Documento {documento_id} no encontrado para el tenant {self.tenant_id}")

        regla = await self._buscar_regla_aprendida(documento.nit_emisor)

        if regla is not None:
            clasificacion = {
                "cuenta_puc": regla.cuenta_puc,
                "categoria_gasto": "Clasificación aprendida de correcciones previas",
                "justificacion": (
                    f"NIT {documento.nit_emisor} tiene una regla aprendida "
                    f"(aplicada {regla.veces_aplicada} veces antes) tras una corrección humana."
                ),
                "requiere_revision_humana": False,
            }
            regla.veces_aplicada += 1
            accion = "clasificacion_por_regla_aprendida"
        else:
            items = (documento.datos_extraidos or {}).get("items", [])
            clasificacion = clasificar_factura_con_claude(
                razon_social_emisor=documento.razon_social_emisor,
                items=items,
                total=float(documento.total),
            )
            accion = "clasificacion_y_causacion"

        retefuente = calcular_retefuente(float(documento.total), concepto_retefuente)
        reteica = calcular_reteica(float(documento.total), tarifa_reteica_por_mil)

        documento.cuenta_puc_sugerida = clasificacion.get("cuenta_puc", "519999")
        documento.retenciones = {"reteFuente": retefuente, "reteICA": reteica}
        documento.estado = (
            EstadoDocumento.APROBACION_PENDIENTE
            if clasificacion.get("requiere_revision_humana")
            else EstadoDocumento.CAUSADO
        )

        await self.db.flush()

        await self.registrar_evento(
            documento.id,
            accion=accion,
            detalle=clasificacion.get("justificacion"),
            resultado={
                "cuenta_puc": documento.cuenta_puc_sugerida,
                "retenciones": documento.retenciones,
                "estado_resultante": documento.estado.value,
            },
        )

        return documento
