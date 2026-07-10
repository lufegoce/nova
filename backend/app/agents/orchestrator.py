"""
Agent Orchestrator (El Cerebro): recibe tareas de alto nivel (ej. "procesar
factura entrante", "conciliar mes") y las desglosa en subtareas, delegando
a los agentes especializados en el orden correcto del ciclo de vida:

  Ingesta (Receptor) -> Procesamiento (Contable) -> Aprobación humana
    -> Ejecución (Pagador) -> Monitoreo (Reportero)

El orquestador NO contiene reglas de negocio contables/bancarias propias;
solo coordina y garantiza que cada paso quede auditado.
"""
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.agente_conciliador import AgenteConciliador
from app.agents.agente_contable import AgenteContable
from app.agents.agente_pagador import AgentePagador
from app.agents.agente_receptor import AgenteReceptor
from app.agents.agente_reportero import AgenteReportero
from app.models.documento import DocumentoFinanciero, TipoDocumento


class AgentOrchestrator:
    def __init__(self, db: AsyncSession, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    async def procesar_documento_entrante(
        self,
        contenido_xml: bytes,
        origen_canal: str = "upload",
        tipo: TipoDocumento = TipoDocumento.FACTURA_COMPRA,
        auto_causar: bool = True,
    ) -> DocumentoFinanciero:
        """Subtarea 1 y 2 del ciclo: ingesta + clasificación/causación propuesta."""
        receptor = AgenteReceptor(self.db, self.tenant_id)
        documento = await receptor.ejecutar(contenido_xml, origen_canal=origen_canal, tipo=tipo)

        if auto_causar:
            contable = AgenteContable(self.db, self.tenant_id)
            documento = await contable.ejecutar(documento.id)

        await self.db.commit()
        return documento

    async def procesar_pdf_manual(
        self,
        contenido_pdf: bytes,
        nit_emisor: str,
        total: float,
        razon_social_emisor: str | None = None,
        numero_factura: str | None = None,
        fecha_emision: datetime | None = None,
        tipo: TipoDocumento = TipoDocumento.FACTURA_COMPRA,
        cufe: str | None = None,
        auto_causar: bool = True,
    ) -> DocumentoFinanciero:
        """Ingesta manual: el humano descargó el PDF desde el portal DIAN y confirma los campos clave."""
        receptor = AgenteReceptor(self.db, self.tenant_id)
        documento = await receptor.ejecutar_desde_pdf(
            contenido_pdf,
            nit_emisor=nit_emisor,
            total=total,
            razon_social_emisor=razon_social_emisor,
            numero_factura=numero_factura,
            fecha_emision=fecha_emision,
            tipo=tipo,
            cufe=cufe,
        )

        if auto_causar:
            contable = AgenteContable(self.db, self.tenant_id)
            documento = await contable.ejecutar(documento.id)

        await self.db.commit()
        return documento

    async def aprobar_y_pagar(
        self,
        documento_id: UUID,
        aprobado_por: str,
        cuenta_puc_corregida: str | None = None,
    ) -> DocumentoFinanciero:
        """
        Subtarea de ejecución: solo se alcanza tras aprobación humana explícita.
        Si el humano corrigió la cuenta PUC sugerida, el Agente Contable guarda
        esa corrección como regla aprendida para el NIT del emisor antes de pagar.
        """
        if cuenta_puc_corregida:
            contable = AgenteContable(self.db, self.tenant_id)
            documento = await self.db.get(DocumentoFinanciero, documento_id)
            if documento is None or documento.tenant_id != self.tenant_id:
                raise ValueError(f"Documento {documento_id} no encontrado para el tenant {self.tenant_id}")
            if cuenta_puc_corregida != documento.cuenta_puc_sugerida:
                await contable.aprender_correccion_humana(documento, cuenta_puc_corregida)

        pagador = AgentePagador(self.db, self.tenant_id)
        documento = await pagador.ejecutar(documento_id, aprobado_por=aprobado_por)
        await self.db.commit()
        return documento

    async def conciliar_periodo(self, movimientos_bancarios: list[dict]) -> dict:
        conciliador = AgenteConciliador(self.db, self.tenant_id)
        resultado = await conciliador.ejecutar(movimientos_bancarios)
        await self.db.commit()
        return resultado

    async def generar_reporte(self) -> dict:
        reportero = AgenteReportero(self.db, self.tenant_id)
        return await reportero.ejecutar()
