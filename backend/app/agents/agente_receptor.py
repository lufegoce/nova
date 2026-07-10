"""
Agente Receptor (RAG): lee y extrae datos de facturas XML/PDF, correos y WhatsApp.

Dos canales soportados en el MVP:
  - XML UBL (`ejecutar`): extracción automática y confiable de todos los campos.
  - PDF subido manualmente (`ejecutar_desde_pdf`): la extracción automática de
    campos desde un PDF arbitrario (representación gráfica de la DIAN) no es
    confiable sin OCR/plantillas dedicadas, así que aquí el humano confirma
    los campos clave al subir el archivo; el PDF se guarda para trazabilidad
    y previsualización, y el Agente Contable sigue el mismo flujo de siempre.

Los canales de email/WhatsApp quedan como puntos de extensión (ver `origen_canal`).
"""
from datetime import datetime

from app.agents.base import AgenteBase
from app.models.documento import DocumentoFinanciero, EstadoDocumento, TipoDocumento
from app.services.pdf_storage import guardar_pdf
from app.services.xml_parser import parsear_factura_xml


class AgenteReceptor(AgenteBase):
    nombre = "agente_receptor"

    async def ejecutar(
        self,
        contenido_xml: bytes,
        origen_canal: str = "upload",
        tipo: TipoDocumento = TipoDocumento.FACTURA_COMPRA,
    ) -> DocumentoFinanciero:
        factura = parsear_factura_xml(contenido_xml)

        documento = DocumentoFinanciero(
            tenant_id=self.tenant_id,
            tipo=tipo,
            estado=EstadoDocumento.NUEVO,
            nit_emisor=factura.nit_emisor,
            razon_social_emisor=factura.razon_social_emisor,
            numero_factura=factura.numero_factura,
            fecha_emision=factura.fecha_emision,
            total=factura.total,
            datos_extraidos={"items": factura.items},
            origen_canal=origen_canal,
        )
        self.db.add(documento)
        await self.db.flush()

        await self.registrar_evento(
            documento.id,
            accion="ingesta_factura",
            detalle=f"Factura {factura.numero_factura} extraída del canal {origen_canal}",
            resultado={"nit_emisor": factura.nit_emisor, "total": factura.total},
        )

        return documento

    async def ejecutar_desde_pdf(
        self,
        contenido_pdf: bytes,
        nit_emisor: str,
        total: float,
        razon_social_emisor: str | None = None,
        numero_factura: str | None = None,
        fecha_emision: datetime | None = None,
        tipo: TipoDocumento = TipoDocumento.FACTURA_COMPRA,
        cufe: str | None = None,
    ) -> DocumentoFinanciero:
        documento = DocumentoFinanciero(
            tenant_id=self.tenant_id,
            tipo=tipo,
            estado=EstadoDocumento.NUEVO,
            nit_emisor=nit_emisor,
            razon_social_emisor=razon_social_emisor,
            numero_factura=numero_factura,
            fecha_emision=fecha_emision,
            total=total,
            datos_extraidos={"items": [], "cufe": cufe},
            origen_canal="pdf_manual",
        )
        self.db.add(documento)
        await self.db.flush()

        documento.ruta_pdf = guardar_pdf(self.tenant_id, documento.id, contenido_pdf)
        await self.db.flush()

        await self.registrar_evento(
            documento.id,
            accion="ingesta_factura_pdf",
            detalle=f"Factura {numero_factura or '(sin número)'} cargada manualmente como PDF",
            resultado={"nit_emisor": nit_emisor, "total": total, "cufe": cufe},
        )

        return documento
