"""
Configuración del tenant: por ahora, la integración con el ERP contable
(SIIGO, Odoo, SAP Business One...) que se usa al aprobar y pagar una factura.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_tenant_id
from app.db.session import get_db
from app.models.erp import ConfiguracionErp
from app.schemas.erp import ConfiguracionErpOut, ConfiguracionErpRequest

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
