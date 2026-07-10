"""Endpoints del Agente de Seguridad: consultar y resolver alertas, disparar un escaneo manual."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.agente_seguridad import AgenteSeguridad
from app.api.deps import get_tenant_id
from app.db.session import get_db
from app.models.seguridad import AlertaSeguridad
from app.schemas.seguridad import AlertaSeguridadOut, ResultadoEscaneoOut

router = APIRouter(prefix="/seguridad", tags=["seguridad"])


@router.get("/alertas", response_model=list[AlertaSeguridadOut])
async def listar_alertas(
    solo_no_resueltas: bool = True,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    condiciones = [AlertaSeguridad.tenant_id == tenant_id]
    if solo_no_resueltas:
        condiciones.append(AlertaSeguridad.resuelta.is_(False))

    result = await db.execute(
        select(AlertaSeguridad).where(*condiciones).order_by(AlertaSeguridad.creado_en.desc())
    )
    return result.scalars().all()


@router.post("/escanear", response_model=ResultadoEscaneoOut)
async def escanear_ahora(
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    agente = AgenteSeguridad(db, tenant_id)
    return await agente.ejecutar_escaneo()


@router.post("/alertas/{alerta_id}/resolver", response_model=AlertaSeguridadOut)
async def resolver_alerta(
    alerta_id: UUID,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    alerta = await db.get(AlertaSeguridad, alerta_id)
    if alerta is None or alerta.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Alerta no encontrada")

    alerta.resuelta = True
    await db.commit()
    await db.refresh(alerta)
    return alerta
