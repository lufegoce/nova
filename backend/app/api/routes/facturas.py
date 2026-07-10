"""
Endpoints del ciclo de vida del documento financiero:
ingesta (Agente Receptor), consulta, aprobación humana y pago (Agente Pagador).
"""
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.agente_pagador import PagoNoAutorizadoError
from app.agents.orchestrator import AgentOrchestrator
from app.api.deps import get_tenant_id
from app.db.session import get_db
from app.models.dian import DocumentoDianListado
from app.models.documento import DocumentoFinanciero, EventoAuditoria
from app.schemas.documento import AprobacionRequest, DocumentoOut, EventoAuditoriaOut
from app.services.pdf_storage import ruta_absoluta
from app.services.xml_parser import XMLParseError

router = APIRouter(prefix="/facturas", tags=["facturas"])


@router.post("/ingesta", response_model=DocumentoOut, status_code=201)
async def ingestar_factura(
    archivo: UploadFile = File(...),
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Agente Receptor: recibe un XML de factura electrónica y lo procesa/causa."""
    contenido = await archivo.read()
    orquestador = AgentOrchestrator(db, tenant_id)
    try:
        documento = await orquestador.procesar_documento_entrante(contenido, origen_canal="upload")
    except XMLParseError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return documento


@router.post("/ingesta-pdf", response_model=DocumentoOut, status_code=201)
async def ingestar_factura_pdf(
    archivo: UploadFile = File(...),
    nit_emisor: str = Form(...),
    total: float = Form(...),
    razon_social_emisor: str | None = Form(None),
    numero_factura: str | None = Form(None),
    fecha_emision: datetime | None = Form(None),
    cufe: str | None = Form(None),
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Ingesta manual: el PDF fue descargado por el humano desde el portal DIAN
    (ver /dian/documentos-recibidos) resolviendo el captcha él mismo. Los
    campos clave los confirma el usuario al subir el archivo, ya que la
    extracción automática desde un PDF arbitrario no es confiable sin OCR.
    """
    if archivo.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(status_code=422, detail="El archivo debe ser un PDF")

    contenido = await archivo.read()
    orquestador = AgentOrchestrator(db, tenant_id)
    documento = await orquestador.procesar_pdf_manual(
        contenido,
        nit_emisor=nit_emisor,
        total=total,
        razon_social_emisor=razon_social_emisor,
        numero_factura=numero_factura,
        fecha_emision=fecha_emision,
        cufe=cufe,
    )

    if cufe:
        result = await db.execute(
            select(DocumentoDianListado).where(
                DocumentoDianListado.tenant_id == tenant_id, DocumentoDianListado.cufe == cufe
            )
        )
        listado = result.scalar_one_or_none()
        if listado is not None:
            listado.estado_descarga = "descargado"
            listado.documento_financiero_id = documento.id
            await db.commit()

    return documento


@router.get("/{documento_id}/pdf")
async def obtener_pdf_factura(
    documento_id: UUID,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    documento = await db.get(DocumentoFinanciero, documento_id)
    if documento is None or documento.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    if not documento.ruta_pdf:
        raise HTTPException(status_code=404, detail="Este documento no tiene PDF almacenado")

    ruta = ruta_absoluta(documento.ruta_pdf)
    if not ruta.exists():
        raise HTTPException(status_code=404, detail="El archivo PDF ya no existe en el almacenamiento")

    return FileResponse(ruta, media_type="application/pdf")


@router.get("", response_model=list[DocumentoOut])
async def listar_facturas(
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DocumentoFinanciero)
        .where(DocumentoFinanciero.tenant_id == tenant_id)
        .order_by(DocumentoFinanciero.creado_en.desc())
    )
    return result.scalars().all()


@router.get("/{documento_id}", response_model=DocumentoOut)
async def obtener_factura(
    documento_id: UUID,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    documento = await db.get(DocumentoFinanciero, documento_id)
    if documento is None or documento.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    return documento


@router.get("/{documento_id}/trazabilidad", response_model=list[EventoAuditoriaOut])
async def trazabilidad_factura(
    documento_id: UUID,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Soporta al Chat Inteligente: '¿por qué no se pagó la factura 123?'."""
    documento = await db.get(DocumentoFinanciero, documento_id)
    if documento is None or documento.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    result = await db.execute(
        select(EventoAuditoria)
        .where(EventoAuditoria.documento_id == documento_id)
        .order_by(EventoAuditoria.creado_en.asc())
    )
    return result.scalars().all()


@router.post("/{documento_id}/aprobar", response_model=DocumentoOut)
async def aprobar_factura(
    documento_id: UUID,
    body: AprobacionRequest,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Human-in-the-loop: valida la propuesta del Agente Contable. Si se aprueba,
    dispara al Agente Pagador. Si se rechaza, solo queda registrado en auditoría.
    """
    orquestador = AgentOrchestrator(db, tenant_id)

    if not body.aprobado:
        documento = await db.get(DocumentoFinanciero, documento_id)
        if documento is None or documento.tenant_id != tenant_id:
            raise HTTPException(status_code=404, detail="Documento no encontrado")
        from app.models.documento import EstadoDocumento
        documento.estado = EstadoDocumento.RECHAZADO
        await db.commit()
        return documento

    try:
        documento = await orquestador.aprobar_y_pagar(
            documento_id,
            aprobado_por=body.aprobado_por,
            cuenta_puc_corregida=body.cuenta_puc_corregida,
        )
    except PagoNoAutorizadoError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return documento
