"""
Endpoints de integración con el catálogo de la DIAN.

Flujo soportado (ver docstring de app/services/dian_portal_connector.py para
el detalle de qué está confirmado contra el portal real y qué no):
  1. El usuario reenvía a NOVA el magic-link que le llegó por correo de la DIAN.
  2. NOVA lo abre, captura la cookie de sesión y la guarda para el tenant.
  3. NOVA lista los documentos recibidos (esto sí es 100% automático).
  4. Para descargar el PDF de un documento, el usuario debe abrir el portal
     real (link "Abrir en DIAN"), resolver el captcha y descargarlo él mismo,
     y luego subirlo a NOVA vía /facturas/ingesta-pdf.
"""
from datetime import date, datetime, timedelta

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_tenant_id
from app.db.session import get_db
from app.models.dian import DocumentoDianListado, SesionDian
from app.models.usuario import Empresa
from app.schemas.dian import DocumentoDianListadoOut, SesionDianOut, VincularSesionRequest
from app.services.dian_portal_connector import (
    DianAuthError,
    extraer_nit_del_magic_link,
    listar_documentos_recibidos,
    mapear_fila_documento,
    url_portal_documentos_recibidos,
    vincular_sesion,
)


def _solo_digitos(valor: str) -> str:
    return "".join(c for c in valor if c.isdigit())

router = APIRouter(prefix="/dian", tags=["dian"])


def _parsear_fecha(valor) -> datetime | None:
    """Coerción defensiva: el formato de fecha real del portal no está confirmado."""
    if not valor:
        return None
    if isinstance(valor, datetime):
        return valor
    texto = str(valor).strip()
    try:
        return datetime.fromisoformat(texto.replace("Z", "+00:00"))
    except ValueError:
        pass
    for formato in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(texto, formato)
        except ValueError:
            continue
    return None


@router.post("/vincular", response_model=SesionDianOut, status_code=201)
async def vincular_sesion_dian(
    body: VincularSesionRequest,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    nit_del_enlace = extraer_nit_del_magic_link(body.magic_link_url)

    empresa_result = await db.execute(select(Empresa).where(Empresa.tenant_id == tenant_id))
    empresa = empresa_result.scalar_one_or_none()

    if nit_del_enlace and empresa:
        if not empresa.nit:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"{empresa.nombre} no tiene NIT configurado, así que no se puede verificar que "
                    "este enlace le pertenezca. Completa el NIT de la empresa antes de vincular la sesión DIAN."
                ),
            )
        if _solo_digitos(nit_del_enlace) != _solo_digitos(empresa.nit):
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Este enlace pertenece al NIT {nit_del_enlace}, pero {empresa.nombre} está "
                    f"registrada con NIT {empresa.nit}. Verifica que el correo de la DIAN sea el "
                    "de esta empresa antes de vincularlo — no se guardó la sesión."
                ),
            )

    try:
        cookies = await vincular_sesion(body.magic_link_url)
    except DianAuthError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    result = await db.execute(select(SesionDian).where(SesionDian.tenant_id == tenant_id))
    sesion = result.scalar_one_or_none()

    if sesion is None:
        sesion = SesionDian(tenant_id=tenant_id, cookies=cookies, nit_vinculado=nit_del_enlace)
        db.add(sesion)
    else:
        sesion.cookies = cookies
        sesion.nit_vinculado = nit_del_enlace
        sesion.actualizado_en = datetime.utcnow()

    await db.commit()
    await db.refresh(sesion)
    return sesion


@router.get("/sesion", response_model=SesionDianOut)
async def obtener_sesion_dian(
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(SesionDian).where(SesionDian.tenant_id == tenant_id))
    sesion = result.scalar_one_or_none()
    if sesion is None:
        raise HTTPException(status_code=404, detail="No hay una sesión DIAN vinculada para este tenant")
    return sesion


@router.get("/portal-url")
async def obtener_url_portal():
    """URL fija del portal para que el humano complete la descarga (ver conector)."""
    return {"url": url_portal_documentos_recibidos()}


@router.get("/documentos-recibidos", response_model=list[DocumentoDianListadoOut])
async def sincronizar_documentos_recibidos(
    fecha_inicio: date | None = None,
    fecha_fin: date | None = None,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(SesionDian).where(SesionDian.tenant_id == tenant_id))
    sesion = result.scalar_one_or_none()
    if sesion is None:
        raise HTTPException(
            status_code=409,
            detail="No hay sesión DIAN vinculada. Reenvía el magic-link del correo a /dian/vincular primero.",
        )

    fecha_fin = fecha_fin or date.today()
    fecha_inicio = fecha_inicio or (fecha_fin - timedelta(days=30))

    try:
        respuesta = await listar_documentos_recibidos(sesion.cookies, fecha_inicio, fecha_fin)
    except DianAuthError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except httpx.HTTPStatusError as exc:
        # El portal de la DIAN falló del lado de ellos (visto en producción: 500
        # intermitente en GetDocumentsPageToken). Distinguir esto de "sin
        # resultados" evita que el usuario piense que no tiene documentos
        # cuando en realidad la DIAN no respondió bien.
        raise HTTPException(
            status_code=502,
            detail=f"El portal de la DIAN no respondió correctamente ({exc.response.status_code}). Intenta de nuevo en unos minutos.",
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Error de red hacia el portal de la DIAN: {exc}") from exc

    filas = respuesta.get("data", []) if isinstance(respuesta, dict) else []

    for fila in filas:
        mapeada = mapear_fila_documento(fila)
        if not mapeada["cufe"]:
            continue  # sin identificador único no se puede deduplicar; se descarta la fila

        stmt = pg_insert(DocumentoDianListado).values(
            tenant_id=tenant_id,
            cufe=mapeada["cufe"],
            partition_key=mapeada["partition_key"],
            nit_emisor=mapeada["nit_emisor"],
            razon_social_emisor=mapeada["razon_social_emisor"],
            numero_documento=mapeada["numero_documento"],
            fecha_emision=_parsear_fecha(mapeada["fecha_emision"]),
            total=str(mapeada["total"]) if mapeada["total"] is not None else None,
            datos_crudos=fila,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[DocumentoDianListado.tenant_id, DocumentoDianListado.cufe],
            set_={"datos_crudos": fila, "visto_en": datetime.utcnow()},
        )
        await db.execute(stmt)

    await db.commit()

    result = await db.execute(
        select(DocumentoDianListado)
        .where(DocumentoDianListado.tenant_id == tenant_id)
        .order_by(DocumentoDianListado.fecha_emision.desc().nullslast())
    )
    return result.scalars().all()
