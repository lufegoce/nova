"""
Agente Pagador: ejecuta pagos a proveedores/empleados vía API bancaria,
SIEMPRE previa aprobación humana explícita (human-in-the-loop), y sincroniza
la causación con el ERP contable del tenant (SIIGO, Odoo, SAP Business One...)
si hay uno configurado.

Restricción clave de diseño: este agente NUNCA transiciona un documento a
PAGADO sin que exista un evento de aprobación humana registrado antes.
La integración bancaria real (transferencia efectiva) se deja como stub
`_ejecutar_transferencia_bancaria` para conectar con el proveedor elegido.
"""
from uuid import UUID

from sqlalchemy import select

from app.agents.base import AgenteBase
from app.models.documento import DocumentoFinanciero, EstadoDocumento
from app.models.erp import ConfiguracionErp
from app.services.erp.base import DocumentoParaErp, ErrorConectorErp
from app.services.erp.factory import obtener_conector_erp


class PagoNoAutorizadoError(Exception):
    pass


class AgentePagador(AgenteBase):
    nombre = "agente_pagador"

    async def ejecutar(self, documento_id: UUID, aprobado_por: str) -> DocumentoFinanciero:
        documento = await self.db.get(DocumentoFinanciero, documento_id)
        if documento is None or documento.tenant_id != self.tenant_id:
            raise ValueError(f"Documento {documento_id} no encontrado para el tenant {self.tenant_id}")

        if documento.estado not in (EstadoDocumento.CAUSADO, EstadoDocumento.APROBACION_PENDIENTE):
            raise PagoNoAutorizadoError(
                f"El documento está en estado '{documento.estado.value}', no es pagable directamente."
            )

        referencia_pago = self._ejecutar_transferencia_bancaria(documento)

        documento.estado = EstadoDocumento.PAGADO
        await self.db.flush()

        await self.registrar_evento(
            documento.id,
            accion="pago_ejecutado",
            detalle=f"Aprobado por {aprobado_por}",
            resultado={"referencia_pago": referencia_pago, "valor": float(documento.total)},
        )

        await self._sincronizar_con_erp(documento)

        return documento

    def _ejecutar_transferencia_bancaria(self, documento: DocumentoFinanciero) -> str:
        """
        Stub de integración bancaria. En producción: llamar a la API del banco
        (Open Finance / API propietaria) usando credenciales gestionadas vía KMS/HSM.
        """
        return f"SIM-PAGO-{documento.id}"

    async def _sincronizar_con_erp(self, documento: DocumentoFinanciero) -> None:
        """
        Empuja la causación al ERP configurado para el tenant. Si no hay ERP
        configurado (o está inactivo), el documento queda con
        erp_estado='no_configurado' — no es un error, es el estado por defecto.
        Un fallo al enviar al ERP NO revierte el pago ya registrado en NOVA:
        queda marcado como erp_estado='error' con el detalle, para que el
        contador lo reintente o lo cause manualmente en el ERP.
        """
        result = await self.db.execute(
            select(ConfiguracionErp).where(
                ConfiguracionErp.tenant_id == self.tenant_id, ConfiguracionErp.activo.is_(True)
            )
        )
        config = result.scalar_one_or_none()

        if config is None:
            documento.erp_estado = "no_configurado"
            await self.db.flush()
            return

        payload = DocumentoParaErp(
            documento_id=str(documento.id),
            tipo=documento.tipo.value,
            nit_emisor=documento.nit_emisor,
            razon_social_emisor=documento.razon_social_emisor,
            numero_factura=documento.numero_factura,
            fecha_emision=documento.fecha_emision.isoformat() if documento.fecha_emision else None,
            total=float(documento.total),
            cuenta_puc=documento.cuenta_puc_sugerida or "",
            retenciones=documento.retenciones or {},
        )

        try:
            conector = obtener_conector_erp(config.tipo_erp, config.credenciales)
            resultado = await conector.enviar_causacion(payload)
        except ErrorConectorErp as exc:
            resultado = None
            documento.erp_estado = "error"
            documento.erp_detalle_error = str(exc)

        if resultado is not None:
            if resultado.exitoso:
                documento.erp_estado = "enviado"
                documento.erp_referencia = resultado.referencia_erp
                documento.erp_detalle_error = None
            else:
                documento.erp_estado = "error"
                documento.erp_detalle_error = resultado.detalle_error

        await self.db.flush()

        await self.registrar_evento(
            documento.id,
            accion="sincronizacion_erp",
            detalle=documento.erp_detalle_error if documento.erp_estado == "error" else "Causación enviada al ERP",
            resultado={
                "erp_tipo": config.tipo_erp.value,
                "erp_estado": documento.erp_estado,
                "erp_referencia": documento.erp_referencia,
            },
        )
