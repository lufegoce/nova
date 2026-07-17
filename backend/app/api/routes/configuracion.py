"""
Configuración del tenant: la integración con el ERP contable (SIIGO, Odoo,
SAP Business One...) que se usa al aprobar y pagar una factura, la
integración con el PST (Factus) para consultar documentos recibidos sin
pasar por el captcha del portal humano de la DIAN, y el buzón de correo que
NOVA vigila para recibir facturas de proveedores directamente por email.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_tenant_id
from app.db.session import get_db
from app.models.correo import ConfiguracionCorreoFacturas
from app.models.erp import ConfiguracionErp
from app.models.pst import ConfiguracionPst
from app.schemas.correo import ConfiguracionCorreoOut, ConfiguracionCorreoRequest
from app.schemas.erp import ConfiguracionErpOut, ConfiguracionErpRequest
from app.schemas.pst import ConfiguracionPstOut, ConfiguracionPstRequest, DocumentoRecibidoPstOut
from app.services.correo_watcher import ErrorCorreoFacturas, probar_conexion as probar_conexion_correo
from app.services.pst.base import ErrorConectorPst, FiltrosDocumentosRecibidos
from app.services.pst.factory import obtener_conector_pst

router = APIRouter(prefix="/configuracion", tags=["configuracion"])


@router.get("/erp", response_model=ConfiguracionErpOut)
async def obtener_configuracion_erp(
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ConfiguracionErp).where(ConfiguracionErp.tenant_id == tenant_id))
    config = result.scalar_one_or_none()
    if config is None:
        raise HTTPException(status_code=404, detail="No hay ERP configurado para este tenant")

    return ConfiguracionErpOut(
        tipo_erp=config.tipo_erp,
        activo=config.activo,
        creado_en=config.creado_en,
        actualizado_en=config.actualizado_en,
        campos_configurados=list(config.credenciales.keys()),
    )


def _pst_a_out(config: ConfiguracionPst) -> ConfiguracionPstOut:
    return ConfiguracionPstOut(
        tipo_pst=config.tipo_pst,
        activo=config.activo,
        creado_en=config.creado_en,
        actualizado_en=config.actualizado_en,
        campos_configurados=list(config.credenciales.keys()),
    )


@router.get("/pst", response_model=ConfiguracionPstOut)
async def obtener_configuracion_pst(
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ConfiguracionPst).where(ConfiguracionPst.tenant_id == tenant_id))
    config = result.scalar_one_or_none()
    if config is None:
        raise HTTPException(status_code=404, detail="No hay PST configurado para este tenant")
    return _pst_a_out(config)


@router.put("/pst", response_model=ConfiguracionPstOut)
async def guardar_configuracion_pst(
    body: ConfiguracionPstRequest,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ConfiguracionPst).where(ConfiguracionPst.tenant_id == tenant_id))
    config = result.scalar_one_or_none()

    if config is None:
        config = ConfiguracionPst(
            tenant_id=tenant_id, tipo_pst=body.tipo_pst, credenciales=body.credenciales, activo=body.activo
        )
        db.add(config)
    else:
        config.tipo_pst = body.tipo_pst
        config.credenciales = body.credenciales
        config.activo = body.activo

    await db.commit()
    await db.refresh(config)
    return _pst_a_out(config)


@router.post("/pst/probar")
async def probar_conexion_pst(
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Solo obtiene el token de acceso — confirma que las credenciales sirven, sin listar nada."""
    result = await db.execute(select(ConfiguracionPst).where(ConfiguracionPst.tenant_id == tenant_id))
    config = result.scalar_one_or_none()
    if config is None:
        raise HTTPException(status_code=404, detail="No hay PST configurado para este tenant")

    conector = obtener_conector_pst(config.tipo_pst, config.credenciales)
    try:
        await conector.probar_conexion()
    except ErrorConectorPst as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"status": "ok"}


@router.get("/pst/documentos-recibidos", response_model=list[DocumentoRecibidoPstOut])
async def listar_documentos_recibidos_pst(
    solo_con_eventos_pendientes: bool | None = None,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ConfiguracionPst).where(ConfiguracionPst.tenant_id == tenant_id))
    config = result.scalar_one_or_none()
    if config is None:
        raise HTTPException(status_code=404, detail="No hay PST configurado para este tenant")

    conector = obtener_conector_pst(config.tipo_pst, config.credenciales)
    try:
        documentos = await conector.listar_recibidos(
            FiltrosDocumentosRecibidos(solo_con_eventos_pendientes=solo_con_eventos_pendientes)
        )
    except ErrorConectorPst as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return [
        DocumentoRecibidoPstOut(
            cufe=d.cufe,
            nit_emisor=d.nit_emisor,
            razon_social_emisor=d.razon_social_emisor,
            numero_documento=d.numero_documento,
            fecha_emision=d.fecha_emision,
            tiene_eventos_pendientes=d.tiene_eventos_pendientes,
        )
        for d in documentos
    ]


@router.put("/erp", response_model=ConfiguracionErpOut)
async def guardar_configuracion_erp(
    body: ConfiguracionErpRequest,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Crea o reemplaza la configuración de ERP del tenant. Enviar `credenciales`
    completo cada vez (no hace merge parcial) para evitar dejar campos viejos
    de un ERP anterior mezclados con el nuevo.
    """
    result = await db.execute(select(ConfiguracionErp).where(ConfiguracionErp.tenant_id == tenant_id))
    config = result.scalar_one_or_none()

    if config is None:
        config = ConfiguracionErp(
            tenant_id=tenant_id,
            tipo_erp=body.tipo_erp,
            credenciales=body.credenciales,
            activo=body.activo,
        )
        db.add(config)
    else:
        config.tipo_erp = body.tipo_erp
        config.credenciales = body.credenciales
        config.activo = body.activo

    await db.commit()
    await db.refresh(config)

    return ConfiguracionErpOut(
        tipo_erp=config.tipo_erp,
        activo=config.activo,
        creado_en=config.creado_en,
        actualizado_en=config.actualizado_en,
        campos_configurados=list(config.credenciales.keys()),
    )


@router.get("/correo", response_model=ConfiguracionCorreoOut)
async def obtener_configuracion_correo(
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ConfiguracionCorreoFacturas).where(ConfiguracionCorreoFacturas.tenant_id == tenant_id)
    )
    config = result.scalar_one_or_none()
    if config is None:
        raise HTTPException(status_code=404, detail="No hay buzón de correo configurado para este tenant")
    return config


@router.put("/correo", response_model=ConfiguracionCorreoOut)
async def guardar_configuracion_correo(
    body: ConfiguracionCorreoRequest,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ConfiguracionCorreoFacturas).where(ConfiguracionCorreoFacturas.tenant_id == tenant_id)
    )
    config = result.scalar_one_or_none()

    if config is None:
        if not body.password:
            raise HTTPException(status_code=422, detail="La contraseña es obligatoria al configurar el buzón por primera vez")
        config = ConfiguracionCorreoFacturas(tenant_id=tenant_id, **body.model_dump())
        db.add(config)
    else:
        for campo, valor in body.model_dump(exclude={"password"}).items():
            setattr(config, campo, valor)
        if body.password:
            config.password = body.password

    await db.commit()
    await db.refresh(config)
    return config


@router.post("/correo/probar")
async def probar_configuracion_correo(
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Solo confirma que las credenciales IMAP sirven, sin procesar ningún correo."""
    result = await db.execute(
        select(ConfiguracionCorreoFacturas).where(ConfiguracionCorreoFacturas.tenant_id == tenant_id)
    )
    config = result.scalar_one_or_none()
    if config is None:
        raise HTTPException(status_code=404, detail="No hay buzón de correo configurado para este tenant")

    try:
        await probar_conexion_correo(config)
    except ErrorCorreoFacturas as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"status": "ok"}
